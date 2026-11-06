# 🤖 Esteira de DataOps & CI/CD no GitHub Actions

Este repositório utiliza o **GitHub Actions** para implementar um pipeline automatizado de **DataOps e CI/CD**, responsável por validar, compilar e orquestrar a execução do Lakehouse na AWS de ponta a ponta.

---

## 📋 Alinhamento com os Requisitos Oficiais (Roteiro do Projeto)

Conforme a **Etapa 6 – DataOps e CI/CD no Projeto**, da documentação oficial do Lakehouse, o pipeline atende aos seguintes pilares obrigatórios:

### 1. Versionamento e Rastreabilidade (Git)
Todo o código de ETL, infraestrutura e fluxos está versionado na branch principal `main`, garantindo histórico de alterações e rastreabilidade.

### 2. Validação Prévia (CI – Continuous Integration)
Antes de autorizar qualquer execução ou modificação na infraestrutura da AWS, o pipeline compila e verifica a integridade dos scripts Python por meio do `py_compile`, bloqueando códigos com erros de sintaxe.

### 3. Deploy e Processamento Automatizado (CD – Continuous Deployment)
Após a aprovação na etapa de CI, o pipeline realiza a execução sequencial e orquestrada das quatro camadas do Lakehouse:

**Legado → Raw → Trusted → Curated**

### 4. Execução Agendada e Recorrente (Cron)
Automação temporal diária que executa todo o processo sem necessidade de intervenção manual.

---

## ⚙️ Estrutura e Explicação do Arquivo YAML

**Arquivo:** `pipeline_legado.yml`

### 1. Gatilhos de Disparo (`on`)

- **`push` na branch `main`:** Dispara a esteira automaticamente a cada atualização nos arquivos de código do projeto, ignorando commits que alterem apenas documentação ou arquivos SQL.
- **`schedule` (`cron: '0 3 * * *'`):** Executa o pipeline diariamente à meia-noite (00:00 BRT / 03:00 UTC).
- **`workflow_dispatch`:** Habilita o botão manual **Run workflow** na interface do GitHub para testes e execuções sob demanda.

### 2. Ambientes e Dependências (`jobs`)

- **`runs-on: ubuntu-latest`:** Cria uma máquina virtual limpa e isolada no GitHub Actions.
- **Setup Python 3.11:** Configura o ambiente de execução.
- **Instalação de dependências:** Prepara as bibliotecas essenciais para o processamento dos dados:
  - `boto3`
  - `pandas`
  - `pyarrow`
  - `openpyxl`
  - `unidecode`

### 3. Fase de CI – Integração Contínua

**Validação estática via `py_compile`**

O pipeline verifica individualmente a sintaxe dos scripts Python do projeto:

| Camada | Script |
|:---|:---|
| Legado | `ETL/legado/legado_upload.py` |
| Raw | `ETL/raw/legado_to_raw.py` |
| Trusted | `ETL/trusted/raw_to_trusted.py` |
| Curated | `ETL/curated/run_ctas_athena.py` |

**Critério de aprovação:** Se qualquer arquivo apresentar erro de sintaxe, o pipeline é interrompido imediatamente, impedindo que a execução avance para a etapa de conexão com a AWS.

### 4. Fase de CD – Deploy Contínuo e Execução na AWS

**Autenticação segura**

A conexão com a AWS é realizada por meio da action `configure-aws-credentials`, utilizando as credenciais armazenadas nos Secrets do repositório:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

**Execução sequencial das camadas do Lakehouse**

1. **Legado:** Ingestão dos arquivos locais para a camada Legado no Amazon S3.
2. **Raw:** Carga dos dados com registro de timestamp, preservando o histórico de ingestões.
3. **Trusted:** Limpeza, tratamento, conversão para o formato Parquet e particionamento por ano/mês.
4. **Curated:** Execução dos comandos CTAS no Amazon Athena para atualização dos indicadores da camada Curated.

---

## 🛠️ Como Utilizar

### 1. Configuração das credenciais AWS

Garanta que as credenciais de acesso à AWS estejam cadastradas nos Secrets do repositório:

**GitHub → Settings → Secrets and variables → Actions**

Cadastre:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### 2. Execução automática

Qualquer commit que atualize os scripts de ETL acionará automaticamente o pipeline, conforme os gatilhos configurados no arquivo YAML.

O acompanhamento das execuções pode ser realizado pela aba **Actions** do GitHub.

### 3. Execução manual

Para executar o processo sob demanda:

1. Acesse a aba **Actions** do repositório.
2. Selecione o workflow correspondente.
3. Clique em **Run workflow**.
4. Aguarde a execução das etapas de validação e processamento.

---

**🚀 Resultado:** Uma esteira automatizada de DataOps e CI/CD, integrando versionamento, validação de código e processamento sequencial das quatro camadas do Lakehouse na AWS.
