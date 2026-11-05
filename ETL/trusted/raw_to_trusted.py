#===== IMPORTAÇÕES versão sei lá qual de tanto que tive que ajustar.
import os
import boto3
import pandas as pd
from unidecode import unidecode


#===== CONFIGURAÇÕES GERAIS
EXCEL_PATH = "1base_mestra/Base_de_dados_mercadinho-Corrigida.xlsx"
LOCAL_OUTPUT_DIR = "ETL/trusted/parquet_output"
BUCKET_NAME = "projeto-mercadinho-erp"


#===== MAPEAMENTO DE GUIAS (DIMENSÕES vs FATOS)
DIMENSOES = [
    'PRODUTO',
    'GRUPO',
    'FORNECEDOR',
    'CLIENTES CONTA',
    'CADASTRO COLABORADORES',
    'TABELA ENCARGOS'
]

FATOS = [
    'VENDAS',
    'ESTOQUE',
    'MOVIMENTACAO',
    'HISTÓRICO FINANCEIRO',
    'FOLHA PAGAMENTO',
    'GASTOS FIXOS',
    'VALORES'
]

IGNORAR = ['FORMULAS']  # guias que não são tabelas de dados


#===== AJUSTES DE TIPOS POR TABELA PARA CORRIGIR A VISUALIZAÇÃO DAS TABELAS NO ATHENA =====##

# Chave = nome da tabela no Glue (depois da limpeza de nomes).
# LEGENDA DE CADA LISTA:
#   datas          -> vira DATE (corta a hora)
#   dinheiro       -> vira número com 2 casas decimais
#   sem_arredondar -> vira número SEM arredondar (alíquotas, porcentagens, quantidades)
#   inteiros       -> vira número inteiro
#   excluir        -> coluna removida da Trusted
#   auto_numerico  -> True = tenta converter para número TODAS as colunas que
#                     sobraram (sem arredondar). Só vira número se a coluna inteira
#                     for numérica; se tiver texto, continua texto.
# Colunas que não aparecem em nenhuma lista continuam como texto.

AJUSTES = {
    "dim_cadastro_colaboradores": {
        "datas": ["registro"],
        "excluir": ["2023_de_janeiro_a_fevereiro"], 
    },
    "dim_clientes_conta": {
        "datas": ["registro", "vencimento"],
        "dinheiro": ["valor_em_aberto"],
        # cnpj fica texto de propósito (como número perderia os zeros à esquerda)
    },
    "dim_fornecedor": {
        "datas": ["registro"],
    },
    "dim_grupo": {
        "datas": ["registro"],
    },
    "dim_produto": {
        "datas": ["registro"],
    },
    "dim_tabela_encargos": {
        # Alíquotas e encargos NÃO podem ser arredondados (7,5% != 8%)
        "datas": ["vigencia_a_partir_de"],
        "auto_numerico": True,
    },
    # fato_estoque: sem ajustes (já estava ok)
    "fato_folha_pagamento": {
        "datas": ["data_admissao", "competencia", "data_pagamento",
                  "vig_inss", "vig_irrf"],
        "dinheiro": ["salario_proporcional", "vale_refeicao_pago",
                     "vale_transporte_concedido", "inss", "base_irrf", "irrf",
                     "desconto_vt", "salario_liquido", "salario_base_mes",
                     "vr_base", "vt_base",
                     "inss_f1", "inss_f2", "inss_f3", "inss_f4",   # faixas (R$)
                     "inss_d1", "inss_d2", "inss_d3", "inss_d4",   # deduções (R$)
                     "irrf_limite"],
        "sem_arredondar": ["inss_a1", "inss_a2", "inss_a3", "inss_a4"],  # alíquotas (%)
        "inteiros": ["dias_trabalhados"],
        # chegou como data 1900-01-03 (o Excel mostra o número 3 como data)
        "excluir": ["linha_hist_vigente"],
    },
    "fato_gastos_fixos": {
        "datas": ["competencia"],
        "dinheiro": ["aluguel", "luz", "agua", "internet", "total_mes"],
    },
    "fato_historico_financeiro": {
        "datas": ["registro"],
    },
    "fato_movimentacao": {
        "datas": ["data_pedido", "data_faturamento",
                  "previsao_de_entrega", "recebido_em"],
        "dinheiro": ["custo", "valor_frete", "custo_total"],
        # total_recebido é (unidades) quantidade (valor 15), então não arredonda
        "sem_arredondar": ["quantidade", "total_recebido"],
        "inteiros": ["ano"],
    },
    "fato_valores": {
        "datas": ["registro", "alteracao"],
    },
    "fato_vendas": {
        "datas": ["registro"],
        "dinheiro": ["parcial", "total_a_pagar"],
        "sem_arredondar": ["desconto", "quantidade"],  # desconto é % (não arredondar)
        "inteiros": ["ano"],
        # hora fica como texto (HH:MM:SS): não existe tipo "só hora" no Parquet/Athena
    },
}


#===== FUNÇÃO: LIMPAR NOME DE COLUNA
def limpar_nome_coluna(coluna):
    coluna_str = str(coluna).strip().lower()
    coluna_sem_acento = unidecode(coluna_str)
    coluna_limpa = (
        coluna_sem_acento
        .replace(" ", "_")
        .replace("-", "_")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "_")
    )
    return coluna_limpa


#===== FUNÇÃO: ACHAR A LINHA DO CABEÇALHO (Por que o Excel é bagunçado e o cabeçalho não é sempre a primeira linha)
def achar_linha_cabecalho(df_bruto, max_linhas=15):
    # O cabeçalho é a primeira linha bem preenchida (60% do máximo)
    contagem = df_bruto.head(max_linhas).notna().sum(axis=1)
    limite = contagem.max() * 0.6
    return int(contagem[contagem >= limite].index[0])


#===== FUNÇÃO: GARANTIR NOMES DE COLUNA ÚNICOS
def nomes_unicos(nomes):
    # Evita colunas repetidas, que o Parquet não aceita
    vistos = {}
    resultado = []
    for n in nomes:
        if n in vistos:
            vistos[n] += 1
            resultado.append(f"{n}_{vistos[n]}")
        else:
            vistos[n] = 0
            resultado.append(n)
    return resultado


#===== FUNÇÃO: AVISAR QUANDO UMA CONVERSÃO PERDE VALORES
def avisar_perdas(nome_tabela, col, antes, depois):
    # Se um valor não conseguiu virar data/número, vira vazio (NULL).
    # O aviso deixa isso visível no log da Action, em vez de passar batido.
    perdidos = int(antes.notna().sum() - depois.notna().sum())
    if perdidos > 0:
        print(f"[AVISO] {nome_tabela}.{col}: {perdidos} valor(es) não convertido(s) viraram vazio")


#===== FUNÇÃO: APLICAR OS AJUSTES DE TIPOS
def aplicar_ajustes(df, nome_tabela):
    cfg = AJUSTES.get(nome_tabela, {})
    tratadas = set()  # colunas que já ganharam um tipo

    # ----- Excluir colunas indesejadas
    for col in cfg.get("excluir", []):
        if col in df.columns:
            df = df.drop(columns=[col])
            print(f"         Coluna excluída: {col}")
        else:
            print(f"[AVISO] {nome_tabela}: coluna '{col}' para excluir não foi encontrada")

    # ----- Datas (corta a hora)
    for col in cfg.get("datas", []):
        if col not in df.columns:
            print(f"[AVISO] {nome_tabela}: coluna de data '{col}' não encontrada")
            continue
        convertida = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
        avisar_perdas(nome_tabela, col, df[col], convertida)
        df[col] = convertida.dt.date  # só a data, sem hora
        tratadas.add(col)

    # ----- Dinheiro (2 casas decimais)
    for col in cfg.get("dinheiro", []):
        if col not in df.columns:
            print(f"[AVISO] {nome_tabela}: coluna de dinheiro '{col}' não encontrada")
            continue
        convertida = pd.to_numeric(df[col], errors="coerce")
        avisar_perdas(nome_tabela, col, df[col], convertida)
        df[col] = convertida.round(2)
        tratadas.add(col)

    # ----- Números sem arredondar (alíquotas, porcentagens, quantidades)
    for col in cfg.get("sem_arredondar", []):
        if col not in df.columns:
            print(f"[AVISO] {nome_tabela}: coluna numérica '{col}' não encontrada")
            continue
        convertida = pd.to_numeric(df[col], errors="coerce")
        avisar_perdas(nome_tabela, col, df[col], convertida)
        df[col] = convertida
        tratadas.add(col)

    # ----- Inteiros
    for col in cfg.get("inteiros", []):
        if col not in df.columns:
            print(f"[AVISO] {nome_tabela}: coluna inteira '{col}' não encontrada")
            continue
        convertida = pd.to_numeric(df[col], errors="coerce")
        avisar_perdas(nome_tabela, col, df[col], convertida)
        df[col] = convertida.round().astype("Int64")  # Int64 aceita vazio
        tratadas.add(col)

    # ----- Automático: converte para número (sem arredondar) as colunas que
    #       forem 100% numéricas. Usado na dim_tabela_encargos.
    if cfg.get("auto_numerico"):
        for col in df.columns:
            if col in tratadas:
                continue
            tentativa = pd.to_numeric(df[col], errors="coerce")
            if tentativa.notna().sum() == df[col].notna().sum() and df[col].notna().sum() > 0:
                df[col] = tentativa
                tratadas.add(col)
                print(f"         Coluna numérica (automático): {col}")

    # ----- O que sobrou vira texto (vazio continua vazio, não vira a palavra "nan")
    for col in df.columns:
        if col not in tratadas:
            df[col] = df[col].astype("string")

    return df


#===== FUNÇÃO PRINCIPAL: PROCESSAR A CAMADA TRUSTED
def processar_camada_trusted():
    print("[INFO] A iniciar o processamento da camada Trusted...")

    #===== Verificar se o Excel existe
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"O arquivo Excel '{EXCEL_PATH}' não foi encontrado.")

    #===== Abrir o Excel e listar as guias
    xls = pd.ExcelFile(EXCEL_PATH)
    print(f"[INFO] Abas encontradas no Excel: {xls.sheet_names}")

    s3_client = boto3.client('s3')

    #===== Percorrer cada guia
    for sheet_name in xls.sheet_names:
        sheet_upper = sheet_name.upper()

        #===== Pular guias que não são dados
        if sheet_upper in IGNORAR:
            print(f"[SKIP] Aba ignorada: '{sheet_name}'")
            continue

        print(f"[PROCESSING] A processar a aba: '{sheet_name}'")

        #===== Ler a guia sem cabeçalho e limpar linhas/colunas vazias
        bruto = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        bruto = bruto.dropna(how='all').dropna(axis=1, how='all')
        bruto = bruto.reset_index(drop=True)

        #===== Descobrir a linha do cabeçalho
        linha = achar_linha_cabecalho(bruto)
        print(f"         Cabeçalho encontrado na linha {linha}")

        #===== Separar dados e cabeçalho
        df = bruto.iloc[linha + 1:].copy()
        df.columns = bruto.iloc[linha]

        #===== Remover colunas sem nome no cabeçalho
        df = df.loc[:, df.columns.notna()]

        #===== Limpar nomes das colunas
        df.columns = nomes_unicos([limpar_nome_coluna(col) for col in df.columns])

        #===== Remover linhas totalmente vazias
        df = df.dropna(how='all')

        #===== Definir tipo (dimensão/fato) e nome da tabela
        if sheet_upper in DIMENSOES:
            tipo = "dimensoes"
            prefixo_nome = "dim_"
        elif sheet_upper in FATOS:
            tipo = "fatos"
            prefixo_nome = "fato_"
        else:
            tipo = "outros"
            prefixo_nome = "aux_"

        nome_tabela = f"{prefixo_nome}{limpar_nome_coluna(sheet_name)}"

        #===== Converter tipos (datas, dinheiro, números) e excluir colunas
        # Antes tudo virava texto. Agora cada coluna ganha o tipo certo.
        df = aplicar_ajustes(df, nome_tabela)

        #===== Gravar o Parquet local (uma pasta por tabela, exigência do crawler)
        # trusted/<tipo>/<nome_tabela>/<nome_tabela>.parquet
        local_dir = f"{LOCAL_OUTPUT_DIR}/{tipo}/{nome_tabela}"
        os.makedirs(local_dir, exist_ok=True)
        local_path = f"{local_dir}/{nome_tabela}.parquet"

        df.to_parquet(local_path, index=False, engine='pyarrow')
        print(f"[SUCCESS] Gerado localmente: {local_path} ({len(df)} linhas)")

        #===== Enviar o Parquet para o S3
        s3_key = f"trusted/{tipo}/{nome_tabela}/{nome_tabela}.parquet"
        print(f"[INFO] A enviar para o S3 -> s3://{BUCKET_NAME}/{s3_key}")
        s3_client.upload_file(local_path, BUCKET_NAME, s3_key)
        print(f"[SUCCESS] Upload concluído para: {s3_key}")

    print("[SUCCESS] Camada Trusted processada e enviada para o S3 com sucesso!")


#===== EXECUÇÃO
if __name__ == "__main__":
    processar_camada_trusted()

    #==== Se deus quiser agora o Glue vai ler os Parquets e criar as tabelas no Athena de forma correta!