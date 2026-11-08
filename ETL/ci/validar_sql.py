# =====================================================================
# CI DE SQL - valida os arquivos de ETL/SQL/curated_ctas/ ANTES de tocar na AWS
# Roda no GitHub Actions sem credenciais e sem rede (so le os arquivos .sql).
# Se qualquer regra falhar, o script termina com erro e a esteira nao chega no CD.
# =====================================================================
import re
import sys
from pathlib import Path

PASTA_SQL = Path("ETL/SQL/curated_ctas")
BANCO_CURATED = "db_mercadinho_curated"
BANCO_TRUSTED = "db_mercadinho_trusted"
BUCKET = "projeto-mercadinho-erp"
OBRIGATORIOS = {1, 2, 3, 4}  # indicadores da pos: nao podem sumir
PADRAO_NOME = re.compile(r"^ind(\d+)_[a-z0-9_]+$")
PROIBIDAS = ("DROP", "DELETE", "TRUNCATE", "INSERT", "UPDATE", "ALTER", "GRANT", "MERGE")


def sem_comentarios(texto):
    texto = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)  # /* ... */
    texto = re.sub(r"--[^\n]*", "", texto)               # -- ate o fim da linha
    return texto


def sem_strings(texto):
    return re.sub(r"'[^']*'", "''", texto)


def parenteses_balanceados(texto):
    nivel = 0
    for c in texto:
        if c == "(":
            nivel += 1
        elif c == ")":
            nivel -= 1
            if nivel < 0:
                return False
    return nivel == 0


def validar(arq):
    erros = []
    nome = arq.stem
    sql = sem_comentarios(arq.read_text(encoding="utf-8"))
    corpo = sql.strip()

    if not PADRAO_NOME.match(nome):
        erros.append("nome fora do padrao indN_descricao (minusculas, numeros e _)")
    if not corpo:
        return erros + ["arquivo vazio (so comentarios ou em branco)"]

    # um unico comando, terminado em ;
    if not corpo.endswith(";") or corpo.count(";") != 1:
        erros.append("deve ter um unico comando terminado em ;")

    limpo = sem_strings(corpo)
    if not parenteses_balanceados(limpo):
        erros.append("parenteses desbalanceados")

    # CREATE TABLE <banco_curated>.<nome do arquivo>
    m = re.search(r"CREATE\s+TABLE\s+([\w\.]+)", corpo, re.I)
    if not m:
        erros.append("falta CREATE TABLE (CTAS)")
    elif m.group(1).lower() != f"{BANCO_CURATED}.{nome}":
        erros.append(f"tabela '{m.group(1)}' deve ser '{BANCO_CURATED}.{nome}'")

    # formato e pasta de destino
    if not re.search(r"format\s*=\s*'PARQUET'", corpo, re.I):
        erros.append("falta format = 'PARQUET'")
    m = re.search(r"external_location\s*=\s*'([^']+)'", corpo, re.I)
    esperado = f"s3://{BUCKET}/curated/{nome}/"
    if not m:
        erros.append("falta external_location")
    elif m.group(1) != esperado:
        erros.append(f"external_location '{m.group(1)}' deve ser '{esperado}'")

    # CTAS de verdade: ) AS SELECT  (ou ) AS WITH ...)
    if not re.search(r"\)\s*AS\s*(SELECT|WITH)\b", corpo, re.I):
        erros.append("falta o AS SELECT depois do WITH (...)")

    # comandos que alteram ou apagam dados nao sao permitidos
    for palavra in PROIBIDAS:
        if re.search(rf"\b{palavra}\b", limpo, re.I):
            erros.append(f"comando proibido: {palavra}")

    # so le da Trusted, sempre com o banco explicito (CTEs locais sao permitidas)
    ctes = {c.lower() for c in re.findall(r"\bWITH\s+(\w+)\s+AS\s*\(", limpo, re.I)}
    ctes |= {c.lower() for c in re.findall(r"\)\s*,\s*(\w+)\s+AS\s*\(", limpo, re.I)}
    lidas = re.findall(r"\b(?:FROM|JOIN)\s+([\w\.]+)", limpo, re.I)
    tabelas_trusted = 0
    for ref in lidas:
        r = ref.lower()
        if "." in r:
            if r.startswith(BANCO_TRUSTED + "."):
                tabelas_trusted += 1
            else:
                erros.append(f"le '{ref}': a Curated so pode ler da {BANCO_TRUSTED}")
        elif r not in ctes:
            erros.append(f"tabela '{ref}' sem o nome do banco")
    if tabelas_trusted == 0:
        erros.append(f"nao le nenhuma tabela da {BANCO_TRUSTED}")
    return erros


def main():
    arquivos = sorted(PASTA_SQL.glob("*.sql"))
    if not arquivos:
        print(f"[ERRO] nenhum .sql encontrado em {PASTA_SQL}")
        return 1

    total_erros = 0
    numeros = {}
    for arq in arquivos:
        erros = validar(arq)
        if erros:
            total_erros += len(erros)
            print(f"[ERRO] {arq.name}")
            for e in erros:
                print(f"       - {e}")
        else:
            print(f"[OK]   {arq.name}")
        m = PADRAO_NOME.match(arq.stem)
        if m:
            numeros.setdefault(int(m.group(1)), []).append(arq.name)

    for n, nomes in sorted(numeros.items()):
        if len(nomes) > 1:
            total_erros += 1
            print(f"[ERRO] numero ind{n} repetido: {', '.join(nomes)}")
    faltando = sorted(OBRIGATORIOS - set(numeros))
    if faltando:
        total_erros += 1
        print("[ERRO] indicador(es) obrigatorio(s) ausente(s): " + ", ".join(f"ind{n}" for n in faltando))

    if total_erros:
        print(f"\nValidacao de SQL FALHOU: {total_erros} problema(s) em {len(arquivos)} arquivo(s).")
        return 1
    print(f"\nValidacao de SQL concluida com sucesso: {len(arquivos)} arquivo(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())