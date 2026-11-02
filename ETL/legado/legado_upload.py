import os
import boto3
from botocore.exceptions import ClientError

# =========================
# CONFIGURAÇÕES
# =========================
BUCKET_NAME = "projeto-mercadinho-erp"
S3_PREFIX = "legado"
FILE_NAME = "1base_mestra/Base_de_dados_mercadinho-Corrigida.xlsx"

S3_KEY = f"{S3_PREFIX}/Base_de_dados_mercadinho-Corrigida.xlsx"

# =========================
# FUNÇÕES
# =========================
def upload_file_to_s3(local_path, bucket, s3_key):
    s3_client = boto3.client("s3")

    try:
        print(f"[INFO] Iniciando upload para a nuvem:")
        print(f"       Origem (Repo): {local_path}")
        print(f"       Destino (S3): s3://{bucket}/{s3_key}")

        s3_client.upload_file(local_path, bucket, s3_key)
        print("[SUCCESS] Upload realizado com sucesso para o S3!")

    except FileNotFoundError:
        print(f"[ERROR] O arquivo '{local_path}' não foi encontrado no repositório clonado.")
        raise

    except ClientError as e:
        print("[ERROR] Falha ao enviar o arquivo para o S3.")
        raise e

# =========================
# EXECUÇÃO
# =========================
if __name__ == "__main__":
    if not os.path.exists(FILE_NAME):
        raise FileNotFoundError(
            f"Arquivo '{FILE_NAME}' não encontrado. Verifique o caminho no repositório."
        )

    upload_file_to_s3(
        local_path=FILE_NAME,
        bucket=BUCKET_NAME,
        s3_key=S3_KEY
    )