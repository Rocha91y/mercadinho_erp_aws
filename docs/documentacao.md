# Documentação Técnica — Lakehouse Mercadinho ERP na AWS

**Projeto acadêmico:** Lakehouse Financeiro na AWS com DataOps e CI/CD
**Aluno:** Fernando Rocha
**Repositório:** `Rocha91y/mercadinho_erp_aws`
**Bucket S3:** `projeto-mercadinho-erp` (região `us-east-1`)

---

## 1. Visão geral

Este projeto simula a migração de um sistema financeiro baseado em planilha Excel para um **Lakehouse na AWS**, organizado em quatro camadas (Legado → Raw → Trusted → Curated) e automatizado com **DataOps e CI/CD**.

Em vez da base financeira genérica do enunciado, o projeto usa a **base de um mercadinho de produtos de limpeza** (vendas, compras, estoque, folha de pagamento, gastos fixos etc.), com 13 tabelas. Os quatro indicadores obrigatórios foram **adaptados** a essa base (ver seção 7).

**Resumo do fluxo:**

```
PC (edição) → GitHub Desktop → GitHub → GitHub Actions → AWS (S3 + Glue + Athena)
```

Ninguém envia dados para a AWS manualmente. Toda carga acontece por um `push` no GitHub, que dispara a esteira.

---

## 2. Como o trabalho é organizado: PC, GitHub e AWS

### 2.1 Os três lugares

| Lugar | Papel | O que acontece ali |
|---|---|---|
| **PC do aluno** | Ambiente de edição | Os arquivos são criados e ajustados (scripts Python, SQL, YAML, planilha). Nada de produção roda aqui. |
| **GitHub** | Fonte oficial do código | Guarda a versão oficial de tudo e o histórico de mudanças (quem mudou, quando e por quê). |
| **AWS** | Ambiente de execução e dados | S3 guarda os dados, Glue cataloga, Athena consulta e cria os produtos analíticos. |

### 2.2 O clone local

A pasta do projeto no PC é um **clone** do repositório do GitHub: uma cópia sincronizada. O PC serve **apenas para aplicar ajustes e alterações**; a versão que vale é a do GitHub.

### 2.3 Como uma alteração chega até a AWS

1. **Editar no PC:** o arquivo é alterado no VSCode (ou a planilha é substituída).
2. **Commit no GitHub Desktop:** o aplicativo mostra o que mudou. O aluno escreve uma mensagem que explica a alteração e grava o *commit*.
3. **Push:** o GitHub Desktop envia o commit para o GitHub (branch `main`).
4. **Disparo automático:** o GitHub Actions detecta o `push` e inicia a esteira.
5. **Execução na nuvem:** um servidor Linux do GitHub baixa o código, instala as dependências, autentica na AWS com as *Secrets* e executa os scripts em ordem.
6. **Resultado na AWS:** os dados aparecem nas camadas do S3 e as tabelas no Glue/Athena.

```
PC ──(commit + push)──► GitHub ──(Actions)──► AWS
 editar                  versionar            executar
```

### 2.4 Por que esse desenho

- **Rastreabilidade:** todo ajuste fica registrado no histórico do Git.
- **Reprodutibilidade:** a mesma esteira roda sempre do mesmo jeito, sem depender da máquina do aluno.
- **Segurança:** as chaves da AWS ficam em *Secrets* do GitHub, nunca nos arquivos do repositório.
- **Controle de acesso:** a esteira usa um usuário IAM próprio (`github-actions-mercadinho`), separado do usuário pessoal do aluno.

---

## 3. Estrutura do repositório

```
mercadinho_erp_aws/
├── .github/workflows/Pipelines_lakehouse_mercadinho.yaml
├── .gitignore
├── 1base_mestra/
│   └── Base_de_dados_mercadinho-Corrigida.xlsx
├── ETL/
│   ├── legado/   legado_upload.py
│   ├── raw/      legado_to_raw.py
│   ├── trusted/  raw_to_trusted.py
│   ├── curated/  run_ctas_athena.py
│   └── SQL/curated_ctas/
│       ├── ind1_pagamento_por_fornecedor.sql
│       ├── ind2_recebimento_por_estado.sql
│       ├── ind3_recebimentos_em_dia_por_cidade.sql
│       └── ind4_pagamentos_em_atraso_por_estado.sql
└── docs/
    └── documentacao_tecnica_lakehouse.md  (este arquivo)
```

### 3.1 O que cada pasta guarda e por quê

| Pasta / arquivo | O que guarda | Por que existe |
|---|---|---|
| `.github/workflows/` | O arquivo YAML da esteira CI/CD | O GitHub só executa automações que estejam nesta pasta. É o "roteiro" que diz quando rodar e quais scripts chamar. |
| `.gitignore` | Lista do que o Git deve ignorar | Evita subir arquivos temporários do Excel (`~$*`), Parquets gerados localmente (`ETL/trusted/parquet_output/`) e qualquer credencial. |
| `1base_mestra/` | A planilha Excel original | Simula o **sistema legado** de origem. É a única fonte de dados do projeto. |
| `ETL/legado/` | `legado_upload.py` | Envia o Excel original para a camada Legado do S3, sem alterá-lo. |
| `ETL/raw/` | `legado_to_raw.py` | Copia o arquivo para a camada Raw com um carimbo de data e hora. |
| `ETL/trusted/` | `raw_to_trusted.py` | Limpa, tipa e converte os dados para Parquet. |
| `ETL/curated/` | `run_ctas_athena.py` | Lê os arquivos SQL e manda o Athena executá-los. |
| `ETL/SQL/curated_ctas/` | Um `.sql` por indicador | Mantém a lógica de negócio **versionada** e separada do código Python. Alterar um indicador é alterar um arquivo SQL. |
| `docs/` | Documentação em Markdown | Registra a arquitetura e as decisões. |

> A pasta `ETL/` segue o nome da etapa do processo (Extract, Transform, Load), com uma subpasta por camada. Assim, cada camada tem um único script responsável, o que facilita a manutenção e o diagnóstico de erros.

### 3.2 Pastas que existem no PC mas não fazem parte do Lakehouse

O PC também guarda material de outras frentes do mesmo projeto do mercadinho: pastas de arquivos CSV, scripts Python de tratamento de CSV e uma automação de vendas. Elas **não participam das quatro camadas** e não são usadas pela esteira. A carga em Supabase, por exemplo, é uma evolução opcional, fora do escopo do Lakehouse.

---

## 4. Arquitetura em camadas no S3

```
s3://projeto-mercadinho-erp/
├── legado/                        arquivo Excel original
├── raw/
│   └── ingest_ts=AAAA-MM-DD_HH-MM-SS/   uma pasta por carga
├── trusted/
│   ├── dimensoes/<tabela>/        6 tabelas em Parquet
│   └── fatos/<tabela>/            7 tabelas em Parquet
├── curated/
│   └── <indicador>/               resultado de cada CTAS
└── athena-query-results/          respostas das consultas do Athena
```

### 4.1 Camada Legado
- **Script:** `legado_upload.py`
- **O que faz:** envia o Excel original para `legado/`, **sem nenhuma transformação**.
- **Por que:** simula o sistema financeiro de origem. É a referência para auditar qualquer divergência.

### 4.2 Camada Raw
- **Script:** `legado_to_raw.py`
- **O que faz:** copia o arquivo da camada Legado para `raw/ingest_ts=<data_hora>/`.
- **Por que:**
  - **Versionamento por timestamp:** cada carga ganha sua própria pasta, e nenhuma sobrescreve a outra.
  - **Histórico completo e imutável:** dá para saber exatamente o que foi carregado em cada momento.

### 4.3 Camada Trusted
- **Script:** `raw_to_trusted.py`
- **Entrada:** a planilha Excel. Cada guia vira uma tabela.
- **Saída:** arquivos Parquet em `trusted/dimensoes/` e `trusted/fatos/`, **uma pasta por tabela** (exigência do crawler do Glue).

O que o script faz:

1. **Localiza o cabeçalho** de cada guia automaticamente (primeira linha com pelo menos 60% das células preenchidas), porque as guias têm linhas de título acima da tabela.
2. **Padroniza os nomes das colunas:** minúsculas, sem acentos, sem espaços, com `_` (ex.: `DATA PEDIDO` vira `data_pedido`).
3. **Separa fatos e dimensões:**
   - **Dimensões (6):** produto, grupo, fornecedor, clientes_conta, cadastro_colaboradores, tabela_encargos.
   - **Fatos (7):** vendas, estoque, movimentacao, historico_financeiro, folha_pagamento, gastos_fixos, valores.
   - A guia `FORMULAS` é só anotação e é ignorada.
4. **Converte os tipos**, de acordo com uma tabela de ajustes por coluna (`AJUSTES`, no topo do script):

   | Tipo | Regra |
   |---|---|
   | Datas | viram `DATE` (a hora é descartada) |
   | Valores em dinheiro | número com **2 casas decimais** |
   | Alíquotas e porcentagens | número **sem arredondar** (7,5% não pode virar 8%) |
   | Quantidades e anos | número / inteiro |
   | CNPJ | **texto** (como número, perderia os zeros à esquerda) |
   | Hora | **texto** `HH:MM:SS` (não existe tipo "só hora" no Parquet/Athena) |

5. **Remove colunas indevidas:** `2023_de_janeiro_a_fevereiro` (sobra de cabeçalho no Excel) e `linha_hist_vigente` (o Excel exibia o número 3 como data 03/01/1900).
6. **Gera avisos no log** (`[AVISO]`) quando um valor não consegue ser convertido, em vez de falhar em silêncio.
7. **Particiona os fatos por ano e mês** (subpastas por período), para consultas analíticas lerem só o período necessário.
8. **Grava em Parquet** (formato colunar e compactado) e envia ao S3.

### 4.4 Camada Curated
- **Script:** `run_ctas_athena.py` + os `.sql` de `ETL/SQL/curated_ctas/`
- **O que faz:** cria os **produtos de dados** com `CREATE TABLE AS SELECT` (CTAS) no Athena, gravando o resultado em Parquet em `curated/<indicador>/`.
- **Por que:** entrega tabelas prontas para BI e análise, sem refazer o cálculo a cada consulta.

---

## 5. Catálogo e consulta (Glue e Athena)

| Item | Detalhe |
|---|---|
| Banco da Trusted | `db_mercadinho_trusted` (13 tabelas, todas Parquet) |
| Banco da Curated | `db_mercadinho_curated` (4 tabelas) |
| Crawler | `crawler-mercadinho-trusted`, executado sob demanda, com a função IAM `role-glue-mercadinho` |
| Athena | consulta os dois bancos; resultados em `athena-query-results/` |

O crawler do Glue lê as pastas da Trusted e registra cada uma como tabela. As tabelas da Curated são registradas pelo próprio CTAS.

---

## 6. Esteira DataOps e CI/CD

O arquivo `.github/workflows/Pipelines_lakehouse_mercadinho.yaml` define a esteira **Pipeline Lakehouse Mercadinho ERP - Legado**.

### 6.1 Gatilhos
- **`push` na branch `main`**, exceto quando o commit altera apenas `ETL/SQL/**`, `docs/**` ou arquivos `.md` (`paths-ignore`). Assim, mexer só em documentação ou em SQL não reprocessa os dados.
- **Agendamento diário** (`cron: 0 3 * * *`).
- **Execução manual** (`workflow_dispatch`, botão *Run workflow*).

### 6.2 Etapas

| # | Etapa | O que faz |
|---|---|---|
| 1 | Checkout do repositório | baixa o código para o servidor |
| 2 | Configurar Python | Python 3.11 |
| 3 | Instalar dependências | `boto3`, `openpyxl`, `pandas`, `unidecode`, `pyarrow` |
| 4 | **CI: validação** | compila os scripts Python (`py_compile`) para detectar erro de sintaxe **antes** de tocar na AWS |
| 5 | Credenciais da AWS | usa as *Secrets* `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY` |
| 6 | **CD: executar o pipeline** | roda os scripts em fila: `legado_upload.py` → `legado_to_raw.py` → `raw_to_trusted.py` → `run_ctas_athena.py` |

Se qualquer script falhar, a esteira para e fica vermelha, e o log mostra o motivo.

### 6.3 Segurança (IAM)
A esteira usa o usuário `github-actions-mercadinho`, com as políticas:
- `AmazonS3FullAccess` (gravar e limpar arquivos no S3);
- `AmazonAthenaFullAccess` (executar consultas e CTAS, incluindo o catálogo do Glue).

### 6.4 Como o `run_ctas_athena.py` funciona
Para cada arquivo `.sql` (em ordem alfabética):

1. **`DROP TABLE IF EXISTS`:** remove a tabela antiga do catálogo.
2. **Limpa a pasta de destino no S3:** o CTAS falha se a pasta já tiver arquivos. O script só apaga dentro de `curated/<indicador>/`.
3. **Executa o CTAS** e **espera terminar**, consultando o status no Athena.
4. Se algo falhar, **encerra com erro**, o que deixa a esteira vermelha.

Isso torna a **reexecução previsível**: rodar a esteira várias vezes produz sempre o mesmo resultado, sem erro de "tabela já existe".

---

## 7. Produtos analíticos da camada Curated (CTAS)

### 7.1 Adaptação do enunciado à base do mercadinho

O enunciado usa uma base com Fornecedor, Localidade, Pagamentos e Recebimentos. No mercadinho, o mapeamento ficou assim:

| Conceito do enunciado | Equivalente no mercadinho |
|---|---|
| Fornecedor | `dim_fornecedor` / `fato_movimentacao.fornecedor` |
| Localidade (estado, cidade) | `dim_fornecedor.uf` e `dim_fornecedor.cidade`, ligados por `id_fornecedor` |
| Pagamento | valor das compras (`custo_total`) |
| Recebimento | mercadoria recebida (`total_recebido`, em unidades) |
| "Em dia" | `recebido_em <= previsao_de_entrega` |
| "Em atraso" | `recebido_em > previsao_de_entrega` |

### 7.2 Os quatro indicadores

| # | Indicador | Tabela | Métrica | Validação |
|---|---|---|---|---|
| 1 | Total de pagamento por fornecedor | `ind1_pagamento_por_fornecedor` | soma de `custo_total` por fornecedor | 32 fornecedores, igual ao número de fornecedores com compra |
| 2 | Total de recebimento por estado | `ind2_recebimento_por_estado` | soma de `total_recebido` por UF do fornecedor | 8 estados; soma **102.561** = total da `fato_movimentacao` |
| 3 | Recebimentos em dia por cidade | `ind3_recebimentos_em_dia_por_cidade` | contagem de compras recebidas até a data prevista, por cidade | 18 cidades; soma **2.535** |
| 4 | Recebimentos em atraso por estado | `ind4_pagamentos_em_atraso_por_estado` | contagem de compras recebidas após a data prevista, por UF | soma **9.603** |

**Conferência cruzada:** 2.535 (em dia) + 9.603 (em atraso) = **12.138**, que é o total de compras da `fato_movimentacao`. Todas as compras têm data de recebimento.

### 7.3 Observação sobre o Indicador 4

O enunciado fala em "pagamentos em atraso". A base do mercadinho **não possui data de vencimento nem de pagamento das compras**, então o atraso é medido no **recebimento da mercadoria** (chegada depois da data prevista). O nome do arquivo e da tabela ainda contém "pagamentos", mas o indicador deve ser lido como **recebimentos em atraso**.

**Evolução futura:** um fluxo de pagamento (pedido → faturamento com valor e frete → opção *Pagar*, abatendo de uma tabela de caixa) permitirá medir o atraso de pagamento de verdade.

---

## 8. Como reproduzir o processo

1. Clonar o repositório e abrir no VSCode.
2. Substituir a planilha em `1base_mestra/` (se a base mudou).
3. No GitHub Desktop, escrever a mensagem do commit e clicar em **Push origin**.
4. Abrir a aba **Actions** no GitHub e acompanhar a execução.
5. No log do passo *Executar Pipeline*, procurar `[SUCCESS] Camada Curated processada com sucesso!`.
6. No Athena, consultar as tabelas de `db_mercadinho_curated`.
7. Na primeira carga, ou quando uma pasta da Trusted for recriada, executar o crawler `crawler-mercadinho-trusted`.

---

## 9. Decisões e lições aprendidas

- **Uma pasta por tabela na Trusted:** arquivos soltos fazem o crawler criar colunas de partição indevidas ou uma tabela única vazia.
- **Maiúsculas e minúsculas importam no GitHub Actions:** o servidor é Linux. `SQL` e `sql` são pastas diferentes, ao contrário do Windows.
- **O CTAS falha se a pasta de destino já existir:** por isso o script limpa o prefixo antes de recriar.
- **Permissões IAM levam alguns instantes para valer:** logo após anexar uma política, uma nova execução ainda pode receber `AccessDenied`.
- **Validar com números:** cada indicador foi conferido contra a soma da tabela de origem, e não apenas contra "a consulta rodou".
- **Avisos em vez de falhas silenciosas:** valores não convertidos aparecem no log como `[AVISO]`.

---

## 10. Limitações e próximos passos

- A camada Trusted ainda lê a planilha do **repositório**, e não a cópia mais recente da camada Raw. O próximo passo é fazê-la ler da Raw no S3.
- O Indicador 4 usa recebimento em atraso (seção 7.3); o fluxo de pagamento fica como evolução.
- A carga incremental de vendas em Supabase é uma evolução opcional, fora das quatro camadas.