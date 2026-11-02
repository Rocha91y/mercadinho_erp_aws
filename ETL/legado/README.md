```markdown
# 🛒 Mercadinho ERP - Pipeline Lakehouse (AWS & GitHub Actions)

Este repositório contém a arquitetura de engenharia de dados em nuvem para o projeto **Mercadinho ERP**, estruturada sob o conceito de **Lakehouse** e automatizada via **GitHub Actions** (CI/CD 100% Cloud-Native).

---

## 📁 Estrutura do Repositório

```text
mercadinho_erp_aws/
│
├── 1base_mestra/
│   └── Base_de_dados_mercadinho-Corrigida.xlsx  # Base de dados original de entrada
│
├── ETL/
│   ├── legado/
│   │   └── legado_upload.py                     # Script responsável pelo upload da camada legado
│   ├── raw/
│   │   └── legado_to_raw.py                     # Processamento e envio para a camada Raw
│   ├── trusted/
│   │   └── raw_to_trusted.py                    # Transformação e limpeza para a camada Trusted
│   └── curated/
│       └── run_ctas_athena.py                   # Consultas CTAS e consolidação na camada Curated
│
└── .github/
    └── workflows/
        └── pipeline.yml                         # Configuração do GitHub Actions (Pipeline ETL)

```

---

## 🚀 O que este script (`legado_upload.py`) faz?

O script `ETL/legado/legado_upload.py` é a porta de entrada do pipeline de dados. Ele executa as seguintes etapas de forma totalmente automatizada na nuvem (sem dependência de caminhos locais):

1. **Validação de Ambiente:** Identifica o ambiente de execução e localiza a base de dados oficial (`1base_de_dados_mercadinho-Corrigida.xlsx`) dentro da pasta `1base_mestra/` no repositório clonado pelo GitHub Actions.


2. **Conexão Segura com a AWS:** Utiliza as credenciais seguras injetadas dinamicamente via *Repository Secrets* (`AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY`) para autenticar no ecossistema AWS através da biblioteca `boto3`.
3. **Ingestão para o S3:** Realiza o upload do arquivo bruto para o Data Lake na AWS, posicionando-o corretamente no bucket **`projeto-mercadinho-erp`** sob o prefixo/pasta **`legado/`**.

---

## ⚙️ Como Funciona a Automação (CI/CD)

Cada vez que um novo `git push` é realizado na branch `main`:

1. O GitHub Actions provisiona um ambiente limpo em Ubuntu (`ubuntu-latest`).
2. O código do repositório e o Python são configurados.
3. As dependências necessárias (`boto3`, `pandas`, `openpyxl`, etc.) são instaladas automaticamente.
4. Os scripts de ETL são executados em sequência sequencial estruturada nas camadas do Lakehouse (**Legado** ➔ **Raw** ➔ **Trusted** ➔ **Curated**).

```

