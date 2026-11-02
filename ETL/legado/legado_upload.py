import os
import boto3
from botocore.exceptions import ClientError

# =========================
# CONFIGURAÇÕES
# =========================
BUCKET_NAME = "projeto-mercadinho-erp"
S3_PREFIX = "legado"
FILE_NAME = "1base_de_dados_mercadinho-Corrigida.xlsx"

# O arquivo está na raiz do repositório clonado pelo GitHub Actions
LOCAL_FILE_PATH = FILE_NAME
S3_KEY = f"{S3_PREFIX}/{FILE_NAME}"

# =========================
# FUNÇÕES
# =========================
def upload_file_to_s3(local_path, bucket, s3_key):
    # No GitHub Actions, o boto3 assume automaticamente as AWS Secrets injetadas no ambiente
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
    if not os.path.exists(LOCAL_FILE_PATH):
        raise FileNotFoundError(
            f"Arquivo '{FILE_NAME}' não encontrado. Certifique-se de que ele foi commitado no repositório."
        )

    upload_file_to_s3(
        local_path=LOCAL_FILE_PATH,
        bucket=BUCKET_NAME,
        s3_key=S3_KEY
    )