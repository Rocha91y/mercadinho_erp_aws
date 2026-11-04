import os
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

# =========================
# CONFIGURAÇÕES
# =========================
BUCKET_NAME = "projeto-mercadinho-erp"
# Caminho correto no S3 onde o legado_upload.py salvou o arquivo
SOURCE_KEY = "legado/Base_de_dados_mercadinho-Corrigida.xlsx"

# =========================
# FUNÇÕES
# =========================
def copiar_legado_para_raw():
    s3_client = boto3.client("s3")
    
    # Gera um timestamp único para a versão do dado na Raw
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest_key = f"raw/ingest_ts={timestamp}/Base_de_dados_mercadinho-Corrigida.xlsx"

    try:
        print(f"[INFO] Iniciando cópia Legado para Raw")
        print(f"       Origem : s3://{BUCKET_NAME}/{SOURCE_KEY}")
        print(f"       Destino: s3://{BUCKET_NAME}/{dest_key}")

        s3_client.copy_object(
            Bucket=BUCKET_NAME,
            CopySource={'Bucket': BUCKET_NAME, 'Key': SOURCE_KEY},
            Key=dest_key
        )
        print("[SUCCESS] Arquivo copiado com sucesso para a camada Raw!")
        return timestamp

    except ClientError as e:
        print("[ERROR] Falha ao copiar arquivo da camada Legado para Raw")
        raise e

if __name__ == "__main__":
    copiar_legado_para_raw()