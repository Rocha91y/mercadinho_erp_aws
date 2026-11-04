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
    'TABELA ENCARGOS', 
    'FORMULAS'
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

# =========================
# FUNÇÕES DE LIMPEZA E UPLOAD
# =========================
def limpar_nome_coluna(coluna):
    coluna_str = str(coluna).strip().lower()
    coluna_sem_acento = unidecode(coluna_str)
    coluna_limpa = coluna_sem_acento.replace(" ", "_").replace("-", "_").replace(".", "").replace("(", "").replace(")", "")
    return coluna_limpa

def processar_camada_trusted():
    print("[INFO] A iniciar o processamento da camada Trusted...")
    
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"O arquivo Excel '{EXCEL_PATH}' não foi encontrado.")

    os.makedirs(f"{LOCAL_OUTPUT_DIR}/dimensoes", exist_ok=True)
    os.makedirs(f"{LOCAL_OUTPUT_DIR}/fatos", exist_ok=True)

    xls = pd.ExcelFile(EXCEL_PATH)
    print(f"[INFO] Abas encontradas no Excel: {xls.sheet_names}")

    s3_client = boto3.client('s3')

    for sheet_name in xls.sheet_names:
        print(f"[PROCESSING] A processar a aba: '{sheet_name}'")
        
        df = pd.read_excel(xls, sheet_name=sheet_name)
        
        # Remove linhas e colunas totalmente vazias
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Limpa os nomes das colunas
        df.columns = [limpar_nome_coluna(col) for col in df.columns]
        
        # Remove colunas 'unnamed'
        df = df.loc[:, ~df.columns.str.startswith('unnamed')]
        
        # Converte para string de forma segura
        for col in df.columns:
            df[col] = df[col].astype(str)

        sheet_upper = sheet_name.upper()
        if sheet_upper in DIMENSOES:
            tipo = "dimensoes"
            prefixo_nome = "dim_"
        elif sheet_upper in FATOS:
            tipo = "fatos"
            prefixo_nome = "fato_"
        else:
            tipo = "outros"
            prefixo_nome = "aux_"

        nome_arquivo_limpo = limpar_nome_coluna(sheet_name)
        file_name = f"{prefixo_nome}{nome_arquivo_limpo}.parquet"
        local_path = f"{LOCAL_OUTPUT_DIR}/{tipo}/{file_name}"

        # Grava o Parquet localmente
        df.to_parquet(local_path, index=False, engine='pyarrow')
        print(f"[SUCCESS] Gerado localmente: {local_path}")

        # Faz o upload para o S3 na camada Trusted
        s3_key = f"trusted/{tipo}/{file_name}"
        print(f"[INFO] A enviar para o S3 -> s3://{BUCKET_NAME}/{s3_key}")
        s3_client.upload_file(local_path, BUCKET_NAME, s3_key)
        print(f"[SUCCESS] Upload concluído para: {s3_key}")

    print("[SUCCESS] Camada Trusted processada e enviada para o S3 com sucesso!")

if __name__ == "__main__":
    processar_camada_trusted()