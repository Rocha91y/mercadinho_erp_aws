#===== IMPORTAÇÕES
import os
import re
import sys
import time
import glob
import boto3


#===== CONFIGURAÇÕES GERAIS
REGION = "us-east-1"
DATABASE = "db_mercadinho_curated"
BUCKET_NAME = "projeto-mercadinho-erp"
ATHENA_OUTPUT = f"s3://{BUCKET_NAME}/athena-query-results/"

# Pasta dos .sql, calculada a partir deste arquivo (funciona na Action e no .bat)
SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SQL", "curated_ctas")

# Segurança: só apaga dados dentro desta pasta do bucket
PREFIXO_PERMITIDO = "curated/"

ESPERA_SEGUNDOS = 2      # intervalo entre consultas ao Athena
TEMPO_MAXIMO = 600       # desiste de uma query após 10 minutos


#===== CLIENTES AWS
athena = boto3.client("athena", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)


#===== FUNÇÃO: MOSTRAR QUAL USUÁRIO AWS A ACTION ESTÁ USANDO
def mostrar_usuario_aws():
    # Ajuda a achar erros de permissão (AccessDenied): mostra só o nome do usuário
    sts = boto3.client("sts", region_name=REGION)
    identidade = sts.get_caller_identity()
    nome = identidade["Arn"].split("/")[-1]
    print(f"[INFO] Usuário AWS em uso: {nome}")


#===== FUNÇÃO: RODAR UMA QUERY NO ATHENA E ESPERAR TERMINAR
def rodar_query(sql, descricao):
    print(f"[INFO] Athena -> {descricao}")
    resposta = athena.start_query_execution(
        QueryString=sql,
        ResultConfiguration={"OutputLocation": ATHENA_OUTPUT},
    )
    query_id = resposta["QueryExecutionId"]

    inicio = time.time()
    while True:
        execucao = athena.get_query_execution(QueryExecutionId=query_id)
        status = execucao["QueryExecution"]["Status"]
        estado = status["State"]

        if estado == "SUCCEEDED":
            print(f"[SUCCESS] {descricao} (id {query_id})")
            return query_id

        if estado in ("FAILED", "CANCELLED"):
            motivo = status.get("StateChangeReason", "sem detalhe")
            raise RuntimeError(f"{descricao} falhou: {motivo}")

        if time.time() - inicio > TEMPO_MAXIMO:
            raise TimeoutError(f"{descricao} passou de {TEMPO_MAXIMO}s")

        time.sleep(ESPERA_SEGUNDOS)


#===== FUNÇÃO: LIMPAR COMENTÁRIOS E PONTO E VÍRGULA DO .SQL
def limpar_sql(texto):
    # Remove linhas de comentário (--) e o ';' final, que o Athena não precisa
    linhas = [l for l in texto.splitlines() if not l.strip().startswith("--")]
    return "\n".join(linhas).strip().rstrip(";").strip()


#===== FUNÇÃO: LER NOME DA TABELA E PASTA DE DESTINO DENTRO DO .SQL
def ler_destino(sql):
    tabela = re.search(r"CREATE\s+TABLE\s+([\w\.]+)", sql, re.IGNORECASE)
    local = re.search(r"external_location\s*=\s*'s3://([^/]+)/([^']+)'", sql, re.IGNORECASE)
    if not tabela or not local:
        raise ValueError("O .sql precisa ter CREATE TABLE e external_location")
    return tabela.group(1), local.group(1), local.group(2)


#===== FUNÇÃO: APAGAR OS ARQUIVOS ANTIGOS DA PASTA DE DESTINO
def limpar_pasta_s3(bucket, prefixo):
    # O CTAS falha se a pasta de destino já tiver arquivos
    if bucket != BUCKET_NAME or not prefixo.startswith(PREFIXO_PERMITIDO) or prefixo == PREFIXO_PERMITIDO:
        raise ValueError(f"Pasta fora do permitido, não vou apagar: s3://{bucket}/{prefixo}")

    apagados = 0
    paginador = s3.get_paginator("list_objects_v2")
    for pagina in paginador.paginate(Bucket=bucket, Prefix=prefixo):
        objetos = [{"Key": o["Key"]} for o in pagina.get("Contents", [])]
        if objetos:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objetos})
            apagados += len(objetos)
    print(f"[INFO] Pasta limpa: s3://{bucket}/{prefixo} ({apagados} arquivo(s) apagado(s))")


#===== FUNÇÃO PRINCIPAL: RODAR OS CTAS DA CURATED
def processar_camada_curated():
    print("[INFO] A iniciar o processamento da camada Curated...")

    #===== Mostrar qual usuário AWS está em uso (para diagnosticar permissões)
    mostrar_usuario_aws()

    #===== Achar os .sql (ordem alfabética: ind1, ind2, ind3, ind4)
    arquivos = sorted(glob.glob(os.path.join(SQL_DIR, "*.sql")))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum .sql encontrado em {SQL_DIR}")
    print(f"[INFO] {len(arquivos)} script(s) encontrado(s)")

    #===== Garantir que o banco da Curated existe
    rodar_query(f"CREATE DATABASE IF NOT EXISTS {DATABASE}", f"Banco {DATABASE}")

    #===== Rodar cada CTAS
    for caminho in arquivos:
        nome_arquivo = os.path.basename(caminho)
        print(f"[PROCESSING] {nome_arquivo}")

        with open(caminho, "r", encoding="utf-8") as f:
            sql = limpar_sql(f.read())

        tabela, bucket, prefixo = ler_destino(sql)

        #===== 1) Apagar a tabela antiga do catálogo (os dados ficam no S3)
        rodar_query(f"DROP TABLE IF EXISTS {tabela}", f"DROP {tabela}")

        #===== 2) Apagar os arquivos antigos do S3
        limpar_pasta_s3(bucket, prefixo)

        #===== 3) Criar a tabela de novo (CTAS)
        rodar_query(sql, f"CTAS {tabela}")

    print("[SUCCESS] Camada Curated processada com sucesso!")


#===== EXECUÇÃO
if __name__ == "__main__":
    try:
        processar_camada_curated()
    except Exception as erro:
        # Sai com erro para a Action (e o .bat) ficarem vermelhos
        print(f"[ERROR] {erro}")
        sys.exit(1)