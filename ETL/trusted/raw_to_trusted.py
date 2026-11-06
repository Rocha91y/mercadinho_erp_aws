#===== IMPORTAÇÕES
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


#===== AJUSTES DE TIPOS POR TABELA =====##
AJUSTES = {
    "dim_cadastro_colaboradores": {
        "datas": ["registro", "nascimento"],
        "excluir": ["2023_de_janeiro_a_fevereiro"],
    },
    "dim_clientes_conta": {
        "datas": ["registro", "vencimento"],
        "dinheiro": ["valor_em_aberto"],
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
        "datas": ["vigencia_a_partir_de"],
        "dinheiro": ["faixa_1_limite", "faixa_2_limite", "faixa_3_limite",
                     "faixa_4___teto_limite",
                     "deducao_1", "deducao_2", "deducao_3", "deducao_4"],
        "sem_arredondar": ["aliq_1", "aliq_2", "aliq_3", "aliq_4"],
        "auto_numerico": True,
    },
    "fato_folha_pagamento": {
        "datas": ["data_admissao", "competencia", "data_pagamento",
                  "vig_inss", "vig_irrf"],
        "dinheiro": ["salario_proporcional", "vale_refeicao_pago",
                     "vale_transporte_concedido", "inss", "base_irrf", "irrf",
                     "desconto_vt", "salario_liquido", "salario_base_mes",
                     "vr_base", "vt_base",
                     "inss_f1", "inss_f2", "inss_f3", "inss_f4",
                     "inss_d1", "inss_d2", "inss_d3", "inss_d4",
                     "irrf_limite"],
        "sem_arredondar": ["inss_a1", "inss_a2", "inss_a3", "inss_a4"],
        "inteiros": ["dias_trabalhados"],
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
        "sem_arredondar": ["quantidade", "total_recebido"],
        "inteiros": ["ano"],
    },
    "fato_valores": {
        "datas": ["registro", "alteracao"],
    },
    "fato_vendas": {
        "datas": ["registro"],
        "dinheiro": ["parcial", "total_a_pagar"],
        "sem_arredondar": ["desconto", "quantidade"],
        "inteiros": ["ano"],
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


#===== FUNÇÃO: ACHAR A LINHA DO CABEÇALHO
def achar_linha_cabecalho(df_bruto, max_linhas=15):
    contagem = df_bruto.head(max_linhas).notna().sum(axis=1)
    limite = contagem.max() * 0.6
    return int(contagem[contagem >= limite].index[0])


#===== FUNÇÃO: GARANTIR NOMES DE COLUNA ÚNICOS
def nomes_unicos(nomes):
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
    perdidos = int(antes.notna().sum() - depois.notna().sum())
    if perdidos > 0:
        print(f"[AVISO] {nome_tabela}.{col}: {perdidos} valor(es) não convertido(s) viraram vazio")


#===== FUNÇÃO: APLICAR OS AJUSTES DE TIPOS
def aplicar_ajustes(df, nome_tabela):
    cfg = AJUSTES.get(nome_tabela, {})
    tratadas = set()

    for col in cfg.get("excluir", []):
        if col in df.columns:
            df = df.drop(columns=[col])
            print(f"        Coluna excluída: {col}")
        else:
            print(f"[AVISO] {nome_tabela}: coluna '{col}' para excluir não foi encontrada")

    for col in cfg.get("datas", []):
        if col not in df.columns:
            print(f"[AVISO] {nome_tabela}: coluna de data '{col}' não encontrada")
            continue
        convertida = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
        avisar_perdas(nome_tabela, col, df[col], convertida)
        df[col] = convertida.dt.date
        tratadas.add(col)

    for col in cfg.get("dinheiro", []):
        if col not in df.columns:
            print(f"[AVISO] {nome_tabela}: coluna de dinheiro '{col}' não encontrada")
            continue
        convertida = pd.to_numeric(df[col], errors="coerce")
        avisar_perdas(nome_tabela, col, df[col], convertida)
        df[col] = convertida.round(2)
        tratadas.add(col)

    for col in cfg.get("sem_arredondar", []):
        if col not in df.columns:
            print(f"[AVISO] {nome_tabela}: coluna numérica '{col}' não encontrada")
            continue
        convertida = pd.to_numeric(df[col], errors="coerce")
        avisar_perdas(nome_tabela, col, df[col], convertida)
        df[col] = convertida
        tratadas.add(col)

    for col in cfg.get("inteiros", []):
        if col not in df.columns:
            print(f"[AVISO] {nome_tabela}: coluna inteira '{col}' não encontrada")
            continue
        convertida = pd.to_numeric(df[col], errors="coerce")
        avisar_perdas(nome_tabela, col, df[col], convertida)
        df[col] = convertida.round().astype("Int64")
        tratadas.add(col)

    if cfg.get("auto_numerico"):
        for col in df.columns:
            if col in tratadas:
                continue
            tentativa = pd.to_numeric(df[col], errors="coerce")
            if tentativa.notna().sum() == df[col].notna().sum() and df[col].notna().sum() > 0:
                df[col] = tentativa
                tratadas.add(col)
                print(f"        Coluna numérica (automático): {col}")

    for col in df.columns:
        if col not in tratadas:
            df[col] = df[col].astype("string")

    return df


#===== FUNÇÃO PRINCIPAL: PROCESSAR A CAMADA TRUSTED
def processar_camada_trusted():
    print("[INFO] A iniciar o processamento da camada Trusted com particionamento...")

    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"O arquivo Excel '{EXCEL_PATH}' não foi encontrado.")

    xls = pd.ExcelFile(EXCEL_PATH)
    print(f"[INFO] Abas encontradas no Excel: {xls.sheet_names}")

    s3_client = boto3.client('s3')

    for sheet_name in xls.sheet_names:
        sheet_upper = sheet_name.upper()

        if sheet_upper in IGNORAR:
            print(f"[SKIP] Aba ignorada: '{sheet_name}'")
            continue

        print(f"[PROCESSING] A processar a aba: '{sheet_name}'")

        bruto = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        bruto = bruto.dropna(how='all').dropna(axis=1, how='all')
        bruto = bruto.reset_index(drop=True)

        linha = achar_linha_cabecalho(bruto)
        print(f"        Cabeçalho encontrado na linha {linha}")

        df = bruto.iloc[linha + 1:].copy()
        df.columns = bruto.iloc[linha]

        df = df.loc[:, df.columns.notna()]
        df.columns = nomes_unicos([limpar_nome_coluna(col) for col in df.columns])
        df = df.dropna(how='all')

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
        df = aplicar_ajustes(df, nome_tabela)

        #===== LÓGICA DE PARTICIONAMENTO (ANO / MÊS) =====
        cfg = AJUSTES.get(nome_tabela, {})
        colunas_datas = cfg.get("datas", [])
        
        coluna_data_encontrada = None
        for c in colunas_datas:
            if c in df.columns:
                coluna_data_encontrada = c
                break

        local_dir = f"{LOCAL_OUTPUT_DIR}/{tipo}/{nome_tabela}"
        
        # Limpa o diretório local da tabela para evitar resíduos de arquivos antigos (ex: full solto)
        if os.path.exists(local_dir):
            for root, dirs, files in os.walk(local_dir, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
        os.makedirs(local_dir, exist_ok=True)

        # Se encontrou coluna de data, particiona estritamente por ano e mês
        if coluna_data_encontrada and not df.empty:
            dt_temp = pd.to_datetime(df[coluna_data_encontrada], errors='coerce')
            df['ano'] = dt_temp.dt.year.fillna(0).astype(int).astype(str)
            df['mes'] = dt_temp.dt.month.fillna(0).astype(int).astype(str).str.zfill(2)
            
            df.to_parquet(
                local_dir,
                index=False,
                engine='pyarrow',
                partition_cols=['ano', 'mes']
            )
            print(f"[SUCCESS] Gerado localmente com particionamento (ano/mes) via '{coluna_data_encontrada}': {local_dir}")
        else:
            # Tabelas sem data salvam arquivo único na raiz da pasta
            local_path = f"{local_dir}/{nome_tabela}.parquet"
            df.to_parquet(local_path, index=False, engine='pyarrow')
            print(f"[SUCCESS] Gerado localmente (sem data/particionamento): {local_path} ({len(df)} linhas)")

        #===== LIMPEZA E UPLOAD PARA O S3 =====
        s3_base_prefix = f"trusted/{tipo}/{nome_tabela}"

        # 1. Limpa os arquivos antigos no S3 para garantir que não fique nenhum arquivo full solto na raiz
        print(f"[INFO] A limpar dados antigos no S3 em s3://{BUCKET_NAME}/{s3_base_prefix}/")
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=f"{s3_base_prefix}/"):
            objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if objects:
                s3_client.delete_objects(Bucket=BUCKET_NAME, Delete={"Objects": objects})

        # 2. Faz o upload da nova estrutura local limpa (seja particionada ou arquivo único)
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_file_path, local_dir)
                s3_key = f"{s3_base_prefix}/{relative_path}".replace("\\", "/")
                
                print(f"[INFO] A enviar -> s3://{BUCKET_NAME}/{s3_key}")
                s3_client.upload_file(local_file_path, BUCKET_NAME, s3_key)

        print(f"[SUCCESS] Upload limpo concluído para a tabela: {nome_tabela}")

    print("[SUCCESS] Camada Trusted processada, limpa e enviada para o S3 com sucesso!")


#===== EXECUÇÃO
if __name__ == "__main__":
    processar_camada_trusted()