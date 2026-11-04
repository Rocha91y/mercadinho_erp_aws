import os
import pandas as pd
from unidecode import unidecode

# =========================
# CONFIGURAÇÕES
# =========================
EXCEL_PATH = "1base_mestra/Base_de_dados_mercadinho-Corrigida.xlsx"
OUTPUT_DIR = "ETL/trusted/parquet_output"

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
# FUNÇÕES DE LIMPEZA
# =========================
def limpar_nome_coluna(coluna):
    coluna_str = str(coluna).strip().lower()
    coluna_sem_acento = unidecode(coluna_str)
    coluna_limpa = coluna_sem_acento.replace(" ", "_").replace("-", "_").replace(".", "")
    return coluna_limpa

def processar_camada_trusted():
    print("[INFO] A iniciar o processamento da camada Trusted...")
    
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"O arquivo Excel '{EXCEL_PATH}' não foi encontrado.")

    os.makedirs(f"{OUTPUT_DIR}/dimensoes", exist_ok=True)
    os.makedirs(f"{OUTPUT_DIR}/fatos", exist_ok=True)

    xls = pd.ExcelFile(EXCEL_PATH)
    print(f"[INFO] Abas encontradas no Excel: {xls.sheet_names}")

    for sheet_name in xls.sheet_names:
        print(f"[PROCESSING] A processar a aba: '{sheet_name}'")
        
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = df.dropna(how='all').dropna(axis=1, how='all')
        df.columns = [limpar_nome_coluna(col) for col in df.columns]

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
        output_path = f"{OUTPUT_DIR}/{tipo}/{prefixo_nome}{nome_arquivo_limpo}.parquet"

        df.to_parquet(output_path, index=False, engine='pyarrow')
        print(f"[SUCCESS] Guardado com sucesso em: {output_path}")

    print("[SUCCESS] Camada Trusted processada com sucesso!")

if __name__ == "__main__":
    processar_camada_trusted()