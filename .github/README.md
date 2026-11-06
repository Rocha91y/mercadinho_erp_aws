# 🚀 Arquitetura de CI/CD e Fluxo de Dados (DataOps)

Este repositório gerencia o pipeline de engenharia de dados de um Lakehouse financeiro na AWS, implementando práticas de **DataOps** e **Integração Contínua (CI/CD)**. 

## 🔄 Fluxo de Execução e Arquitetura

O ecossistema do projeto opera em três ambientes integrados:

1. **Ambiente Local (`PL-AWS`):**
   * Onde o código-fonte, os scripts de ETL (`legado_upload.py`, `legado_to_raw.py`, `trusted.py`) e a base mestre (`1base_mestra/`) são desenvolvidos e versionados.
   * Qualquer alteração local é commitada e enviada via **GitHub Desktop**.

2. **Repositório e Automação (`GitHub & GitHub Actions`):**
   * A pasta `.github/workflows/` abriga os arquivos **YAML** que automatizam a pipeline.
   * Sempre que ocorre um `push` no repositório, o GitHub Actions aciona os scripts de forma automatizada, utilizando **GitHub Secrets** para injetar as credenciais da AWS com total segurança (sem expor chaves no código).

3. **Camadas do Data Lake na Nuvem (`AWS S3`):**
   * **Legado:** Recebe o arquivo original cru via upload automatizado.
   * **Raw:** Replica o arquivo aplicando versionamento por *timestamp* (`ingest_ts`), mantendo o histórico imune a tratamentos (ETL).
   * **Trusted:** Executa as transformações, conversões de tipos, padronização de colunas, conversão para **Parquet** e particionamento analítico por `ano/mes`.

## 📂 Estrutura de Pastas do Repositório

- `.github/workflows/`: Pipelines de CI/CD que disparam a automação para a AWS.
- `1base_mestra/`: Contém a planilha base (`Base_de_dados_mercadinho-Corrigida.xlsx`).
- `ETL/`: Scripts Python de orquestração das camadas (Legado, Raw e Trusted).
- `SQL/`: Scripts de consultas e criação dos produtos analíticos (Camada Curated via CTAS no Athena).
