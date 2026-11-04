import os
import boto3
import pandas as pd
from unidecode import unidecode

# =========================
# CONFIGURAÇÕES
# =========================
EXCEL_PATH = "1base_mestra/Base_de_dados_mercadinho-Corrigida.xlsx"
LOCAL_OUTPUT_DIR = "ETL/trusted/parquet_output"
BUCKET_NAME = "projeto-mercadinho-erp"

# =========================
# MAPEAMENTO DE GUIAS (DIMENSÕES vs FATOS)
# =========================
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

# =========================
# FUNÇÕES
# =========================
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


def achar_linha_cabecalho(df_bruto, max_linhas=15):
    # O cabeçalho é a primeira linha bem preenchida (60% do máximo)
    contagem = df_bruto.head(max_linhas).notna().sum(axis=1)
    limite = contagem.max() * 0.6
    return int(contagem[contagem >= limite].index[0])


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


def processar_camada_trusted():
    print("[INFO] A iniciar o processamento da camada Trusted...")

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

        # Lê sem cabeçalho e descobre em que linha ele está
        bruto = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        bruto = bruto.dropna(how='all').dropna(axis=1, how='all')
        bruto = bruto.reset_index(drop=True)

        linha = achar_linha_cabecalho(bruto)
        print(f"         Cabeçalho encontrado na linha {linha}")

        df = bruto.iloc[linha + 1:].copy()
        df.columns = bruto.iloc[linha]

        # Remove colunas sem nome no cabeçalho
        df = df.loc[:, df.columns.notna()]

        # Limpa os nomes das colunas
        df.columns = nomes_unicos([limpar_nome_coluna(col) for col in df.columns])

        # Remove linhas totalmente vazias
        df = df.dropna(how='all')

        # Converte para string de forma segura
        for col in df.columns:
            df[col] = df[col].astype(str)

        if sheet_upper in DIMENSOES:
            tipo = "dimensoes"
            prefixo_nome = "dim_"
        elif sheet_upper in FATOS:
            tipo = "fatos"
            prefixo_nome = "fato_"
        else:
            tipo = "outros"
            prefixo_nome = "aux_"

        # Uma pasta por tabela: trusted/<tipo>/<nome_tabela>/<nome_tabela>.parquet
        nome_tabela = f"{prefixo_nome}{limpar_nome_coluna(sheet_name)}"
        local_dir = f"{LOCAL_OUTPUT_DIR}/{tipo}/{nome_tabela}"
        os.makedirs(local_dir, exist_ok=True)
        local_path = f"{local_dir}/{nome_tabela}.parquet"

        df.to_parquet(local_path, index=False, engine='pyarrow')
        print(f"[SUCCESS] Gerado localmente: {local_path} ({len(df)} linhas)")

        s3_key = f"trusted/{tipo}/{nome_tabela}/{nome_tabela}.parquet"
        print(f"[INFO] A enviar para o S3 -> s3://{BUCKET_NAME}/{s3_key}")
        s3_client.upload_file(local_path, BUCKET_NAME, s3_key)
        print(f"[SUCCESS] Upload concluído para: {s3_key}")

    print("[SUCCESS] Camada Trusted processada e enviada para o S3 com sucesso!")


if __name__ == "__main__":
    processar_camada_trusted()