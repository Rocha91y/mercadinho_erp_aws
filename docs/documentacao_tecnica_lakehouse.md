# Documentação Técnica — Lakehouse Mercadinho ERP na AWS

**Projeto acadêmico:** Lakehouse Financeiro na AWS com DataOps e CI/CD
**Aluno:** Fernando Rocha
**Repositório:** `Rocha91y/mercadinho_erp_aws`
**Bucket S3:** `projeto-mercadinho-erp` (região `us-east-1`)
**Consumo analítico:** Power BI Desktop, conectado à camada Curated via Amazon Athena (seção 9)
**Última atualização:** 10/11/2026 (agendamento da esteira movido do cron do GitHub para o Amazon EventBridge; ver `docs/otimizando_automacao.md`)

---

## 1. Visão geral

Este projeto simula a migração de um sistema financeiro baseado em planilha Excel para um **Lakehouse na AWS**, organizado em quatro camadas (Legado → Raw → Trusted → Curated) e automatizado com **DataOps e CI/CD**.

Em vez da base financeira genérica do enunciado, o projeto usa a **base de um mercadinho de produtos de limpeza** (vendas, compras, estoque, folha de pagamento, gastos fixos etc.), com 13 tabelas. Os quatro indicadores obrigatórios foram **adaptados** a essa base (ver seção 7). Além deles, o projeto entrega **quatro indicadores complementares de vendas** (ind5 a ind8), um dashboard no Power BI e uma validação automática (CI) tanto dos scripts Python quanto dos arquivos SQL.

**Resumo do fluxo:**

```
PC (edição) → GitHub Desktop → GitHub → GitHub Actions → AWS (S3 + Glue + Athena)
```

Ninguém envia dados para a AWS manualmente. Toda carga acontece por um `push` no GitHub ou por um disparo agendado do Amazon EventBridge, e ambos acionam a esteira.

Depois da camada Curated, o **Power BI** consome as tabelas prontas por meio do Athena (seção 9).

---

## 2. Como o trabalho é organizado: PC, GitHub e AWS

### 2.1 Os três lugares

| Lugar | Papel | O que acontece ali |
|---|---|---|
| **PC do aluno** | Ambiente de edição | Os arquivos são criados e ajustados (scripts Python, SQL, YAML, planilha). Nada de produção roda aqui. |
| **GitHub** | Fonte oficial do código | Guarda a versão oficial de tudo e o histórico de mudanças (quem mudou, quando e por quê). |
| **AWS** | Ambiente de execução e dados | S3 guarda os dados, Glue cataloga, Athena consulta e cria os produtos analíticos. O EventBridge agenda o disparo da esteira. |

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
├── .github/workflows/pipeline_lakehouse_mercadinho.yaml
├── .gitignore
├── 1base_mestra/
│   └── Base_de_dados_mercadinho-Corrigida.xlsx
├── ETL/
│   ├── legado/   legado_upload.py
│   ├── raw/      legado_to_raw.py
│   ├── trusted/  raw_to_trusted.py
│   ├── curated/  run_ctas_athena.py
│   ├── ci/       validar_sql.py
│   └── SQL/curated_ctas/
│       ├── ind1_pagamento_por_fornecedor.sql
│       ├── ind2_recebimento_por_estado.sql
│       ├── ind3_recebimentos_em_dia_por_cidade.sql
│       ├── ind4_recebimentos_em_atraso_por_cidade.sql
│       ├── ind5_faturamento_por_grupo.sql
│       ├── ind6_vendas_por_produto.sql
│       ├── ind7_vendas_por_pagamento.sql
│       └── ind8_faturamento_por_mes.sql
└── docs/
    ├── documentacao_tecnica_lakehouse.md  (este arquivo)
    └── otimizando_automacao.md            (disparo da esteira pelo EventBridge)
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
| `ETL/ci/` | `validar_sql.py` | CI de SQL: valida os arquivos `.sql` antes de qualquer contato com a AWS (seção 6.5). |
| `ETL/SQL/curated_ctas/` | Um `.sql` por indicador (ind1 a ind8) | Mantém a lógica de negócio **versionada** e separada do código Python. Alterar um indicador é alterar um arquivo SQL. |
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
- **Entrada:** a cópia mais recente da planilha na camada Raw (`raw/ingest_ts=...`). Cada guia vira uma tabela.
- **Saída:** arquivos Parquet em `trusted/dimensoes/` e `trusted/fatos/`, **uma pasta por tabela** (exigência do crawler do Glue).

O que o script faz:

1. **Localiza o cabeçalho** de cada guia automaticamente (primeira linha com pelo menos 60% das células preenchidas), porque as guias têm linhas de título acima da tabela.
2. **Padroniza os nomes das colunas:** minúsculas, sem acentos, sem espaços, com `_` (ex.: `DATA PEDIDO` vira `data_pedido`).
3. **Separa fatos e dimensões:**
   - **Dimensões (6):** produto, grupo, fornecedor, clientes_conta, cadastro_colaboradores, tabela_encargos.
   - **Fatos (7):** vendas, estoque, movimentacao, historico_financeiro, folha_pagamento, gastos_fixos, valores.
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
7. **Particiona por ano e mês** as tabelas que possuem coluna de data
   (fatos e dimensões), em subpastas `ano=AAAA/mes=MM`, para que as
   consultas analíticas leiam só o período necessário. Tabelas sem
   coluna de data, como o `fato_estoque`, são gravadas em um único arquivo.
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
| Banco da Curated | `db_mercadinho_curated` (8 tabelas: ind1 a ind8) |
| Crawler | `crawler-mercadinho-trusted`, executado sob demanda, com a função IAM `role-glue-mercadinho` |
| Athena | consulta os dois bancos; resultados em `athena-query-results/` |

O crawler do Glue lê as pastas da Trusted e registra cada uma como tabela. As tabelas da Curated são registradas pelo próprio CTAS.

---

## 6. Esteira DataOps e CI/CD

O arquivo `.github/workflows/pipeline_lakehouse_mercadinho.yaml` define a esteira **Pipeline Lakehouse Mercadinho ERP - Legado**.

### 6.1 Gatilhos
- **`push` na branch `main`:** qualquer alteração enviada ao repositório
  (código, SQL, planilha ou documentação) dispara a esteira. Isso garante
  que a AWS esteja sempre alinhada com o que está versionado no GitHub.
- **Disparo agendado pelo Amazon EventBridge (a cada 3 horas):** uma regra do EventBridge chama a API do GitHub e aciona o workflow via `workflow_dispatch`, no minuto 33 de cada 3ª hora (cron da AWS, em UTC: `cron(33 0/3 * * ? *)`). Esse disparo aparece no GitHub como "Manually run", porque todo disparo por API é considerado manual. **O passo a passo completo está em `docs/otimizando_automacao.md`.**
- **Execução manual** (`workflow_dispatch`, botão *Run workflow*).

> ### ~~Agendamento pelo cron do GitHub (`schedule`)~~ — **REMOVIDO em 10/11/2026**
>
> ~~Agendamento três vezes ao dia, em horários fora da hora cheia (o cron do GitHub é em UTC):~~
>
> | ~~Cron (UTC)~~ | ~~Horário em Brasília~~ |
> |---|---|
> | ~~`47 3 * * *`~~ | ~~00:47~~ |
> | ~~`23 9 * * *`~~ | ~~06:23~~ |
> | ~~`41 21 * * *`~~ | ~~18:41~~ |
>
> **Por que foi removido:** o cron do GitHub Actions funciona em "melhor esforço" e atrasa muito quando há fila, mesmo com minutos "quebrados". Com o cron original (`0 3 * * *`), a execução chegou a iniciar mais de 6 horas depois do previsto. O agendamento foi então passado para o Amazon EventBridge, que é pontual.
>
> **Veja o novo arquivo `docs/otimizando_automacao.md`**, que explica tudo o que foi feito.

**Fila única (`concurrency`):** só uma execução roda por vez. Se um `push` e um disparo do EventBridge coincidirem, a segunda espera a primeira terminar, porque o CTAS apaga e recria as pastas de destino na Curated e duas execuções simultâneas disputariam os mesmos arquivos.

### 6.2 Etapas

| # | Etapa | O que faz |
|---|---|---|
| 1 | Checkout do repositório | baixa o código para o servidor |
| 2 | Configurar Python | Python 3.11 |
| 3 | Instalar dependências | `boto3`, `openpyxl`, `pandas`, `unidecode`, `pyarrow` |
| 4 | **CI: sintaxe do Python** | compila os scripts Python (`py_compile`), incluindo o próprio `validar_sql.py`, para detectar erro de sintaxe **antes** de tocar na AWS |
| 5 | **CI: validação do SQL** | roda `ETL/ci/validar_sql.py` e confere os arquivos `.sql` da Curated (seção 6.5), também **antes** da AWS |
| 6 | Credenciais da AWS | usa as *Secrets* `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY` |
| 7 | **CD: executar o pipeline** | roda os scripts em fila: `legado_upload.py` → `legado_to_raw.py` → `raw_to_trusted.py` → `run_ctas_athena.py` |

Se qualquer etapa falhar, a esteira para e fica vermelha, e o log mostra o motivo. Como os dois passos de CI vêm antes das credenciais da AWS, um erro de código ou de SQL nunca chega a tocar a nuvem.

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

### 6.5 CI de SQL (`ETL/ci/validar_sql.py`)

O script lê todos os `.sql` de `ETL/SQL/curated_ctas/` e não precisa de credenciais nem de rede. Para cada arquivo, confere:

| Regra | Por que existe |
|---|---|
| Nome no padrão `indN_descricao` (minúsculas, números e `_`) | O nome do arquivo é a chave de tudo: tabela, pasta no S3 e ordem de execução. |
| Um único comando, terminado em `;`, com parênteses balanceados | Erro de digitação é pego antes de ir para o Athena. |
| `CREATE TABLE db_mercadinho_curated.<nome do arquivo>` | Evita tabela com nome diferente do arquivo, que a esteira não saberia apagar na reexecução. |
| `format = 'PARQUET'` e `external_location = 's3://projeto-mercadinho-erp/curated/<nome do arquivo>/'` | Evita o erro clássico de copiar um SQL e esquecer de trocar a pasta de destino, o que faria um indicador sobrescrever outro. |
| `) AS SELECT` (ou `AS WITH`) | Garante que é um CTAS completo. |
| Nenhum `DROP`, `DELETE`, `TRUNCATE`, `INSERT`, `UPDATE`, `ALTER`, `GRANT` ou `MERGE` | O SQL de indicador só cria a tabela. Quem apaga é o `run_ctas_athena.py`, de forma controlada. |
| Só lê tabelas de `db_mercadinho_trusted`, sempre com o nome do banco | A Curated é construída a partir da Trusted. Tabelas locais (`WITH ... AS`) são permitidas. |
| Nenhum número `indN` repetido | Dois arquivos com o mesmo número indicam cópia esquecida. |
| ind1 a ind4 presentes | Os quatro indicadores da pós não podem sumir por acidente. |

Se qualquer regra falhar, o script imprime `[ERRO]` com o motivo e termina com código 1, o que deixa a esteira vermelha antes do CD. Se tudo passar, imprime `Validação de SQL concluída com sucesso`.

O script foi testado com os indicadores reais (ind3 a ind8) e com arquivos propositalmente quebrados: pasta de destino errada, tabela com nome diferente do arquivo, parêntese faltando, tabela sem banco, número repetido, comando `DROP` e indicador obrigatório ausente. Todos os erros foram detectados.

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

### 7.2 Os quatro indicadores da pós

| # | Indicador | Tabela | Métrica | Validação |
|---|---|---|---|---|
| 1 | Total de pagamento por fornecedor | `ind1_pagamento_por_fornecedor` | soma de `custo_total` por fornecedor | 32 fornecedores, igual ao número de fornecedores com compra |
| 2 | Total de recebimento por estado | `ind2_recebimento_por_estado` | soma de `total_recebido` por UF do fornecedor | 8 estados; soma **102.561** = total da `fato_movimentacao` |
| 3 | Recebimentos em dia por cidade | `ind3_recebimentos_em_dia_por_cidade` | contagem de compras recebidas até a data prevista, por cidade | 18 cidades; soma **2.535** |
| 4 | Recebimentos em atraso por cidade | `ind4_recebimentos_em_atraso_por_cidade` | contagem de compras recebidas após a data prevista, por cidade | soma **9.603** |

**Conferência cruzada:** 2.535 (em dia) + 9.603 (em atraso) = **12.138**, que é o total de compras da `fato_movimentacao`. Todas as compras têm data de recebimento.

### 7.3 Definição do Indicador 4

O Indicador 4 mede os **recebimentos em atraso**: compras cuja data de recebimento (`recebido_em`) é posterior à data prevista (`previsao_de_entrega`), agrupadas por **cidade** do fornecedor.

O enunciado fala em *pagamentos* em atraso, mas a base do mercadinho não tem data de pagamento: só a data prevista e a data real de recebimento. Por isso o indicador usa o **recebimento em atraso** como equivalente (seção 7.1).

### 7.4 Por que o Indicador 4 é por cidade

O Indicador 4 é o espelho do Indicador 3 e usa a mesma granularidade (cidade) e o mesmo `JOIN` com `dim_fornecedor`. Assim os dois podem ser comparados cidade a cidade e somados (2.535 + 9.603 = 12.138). Um atraso por estado ao lado de um prazo por cidade misturaria dois níveis geográficos no mesmo visual.

Na primeira versão, o Indicador 4 foi construído por estado. Ao trocar para cidade, a tabela e a pasta da versão antiga (`ind4_recebimentos_em_atraso_por_estado`) precisam ser removidas manualmente do Athena (`DROP TABLE`) e do S3, porque o `run_ctas_athena.py` só limpa o que existe nos `.sql` atuais.

### 7.5 Indicadores complementares de vendas (ind5 a ind8)

Além dos quatro da pós, o projeto entrega quatro indicadores sobre a `fato_vendas`. Todos usam `total_a_pagar` (valor da linha já com desconto) e saem com **2 casas decimais** (`DECIMAL(18,2)`).

| # | Indicador | Tabela | Métricas | Dimensão |
|---|---|---|---|---|
| 5 | Faturamento por grupo de produto | `ind5_faturamento_por_grupo` | faturamento, itens vendidos, nº de vendas | grupo (`fato_vendas` → `dim_produto` → `dim_grupo`) |
| 6 | Vendas e rentabilidade por produto | `ind6_vendas_por_produto` | itens vendidos, faturamento, lucro estimado, margem % | produto (`fato_vendas` → `dim_produto`) |
| 7 | Vendas por forma de pagamento | `ind7_vendas_por_pagamento` | nº de vendas, faturamento, ticket médio | forma de pagamento |
| 8 | Faturamento por mês | `ind8_faturamento_por_mes` | faturamento, nº de vendas, itens vendidos | ano e mês |

**Critério de validação (o mesmo para os quatro):**
- A soma do `faturamento` de cada indicador deve ser igual a `SUM(total_a_pagar)` da `fato_vendas`. Se um `JOIN` perder ou duplicar linhas, a soma diverge e o erro aparece.
- Os `JOIN` não duplicam registros: a `dim_produto` tem 1.019 linhas para 1.019 produtos distintos, e a `dim_grupo` tem 8 linhas para 8 grupos distintos.
- O faturamento por ano (`ind8`) pode ser comparado com os totais anuais da base.

**Regras de cálculo:**
- **Nº de vendas:** `COUNT(DISTINCT id_venda)`, porque o `id_venda` se repete quando a venda tem mais de um item.
- **Ticket médio (ind7):** faturamento dividido pelo nº de vendas.
- **Margem % (ind6):** `(preço de venda − custo) ÷ preço de venda`, com o custo e o preço do cadastro atual de produtos.
- **Lucro estimado (ind6):** faturamento menos `quantidade × custo` do cadastro atual. É uma estimativa, porque usa o custo vigente e não o custo da época de cada venda.
- **Custo e venda como texto:** na `dim_produto`, as colunas `custo` e `venda` estão como texto na Trusted. O `ind6` converte com `TRY_CAST` (trocando vírgula por ponto), em uma tabela temporária local (`WITH prod AS`).

---

## 8. Como reproduzir o processo

1. Clonar o repositório e abrir no VSCode.
2. Substituir a planilha em `1base_mestra/` (se a base mudou).
3. No GitHub Desktop, escrever a mensagem do commit e clicar em **Push origin**.
4. Abrir a aba **Actions** no GitHub e acompanhar a execução.
5. No log do passo *Executar Pipeline*, procurar `[SUCCESS] Camada Curated processada com sucesso!`.
6. No Athena, consultar as tabelas de `db_mercadinho_curated`.
7. Na primeira carga, ou quando uma pasta da Trusted for recriada, executar o crawler `crawler-mercadinho-trusted`.
8. No Power BI Desktop, conectar pelo DSN do Athena (seção 9.1) e importar as tabelas de `db_mercadinho_curated`.
9. Depois de cada execução da esteira, clicar em **Atualizar** no Power BI para trazer os dados novos.

---

## 9. Camada de consumo: Power BI

O Power BI Desktop consome **somente a camada Curated**, nunca a Trusted nem a Raw. A separação entre transformação (esteira) e consumo (dashboard) fica clara: quem constrói o indicador é o SQL do CTAS, e o Power BI apenas o exibe.

### 9.1 Conexão com o Athena

| Item | Valor |
|---|---|
| Driver | Amazon Athena ODBC (64 bits) |
| DSN (Fontes de Dados ODBC 64 bits) | `Athena-Lake-House-Mercadinho` |
| Região | `us-east-1` |
| Catálogo | `AwsDataCatalog` |
| Workgroup | `primary` |
| Banco | `db_mercadinho_curated` |
| Saída das consultas | `s3://projeto-mercadinho-erp/athena-query-results/` |
| Autenticação | IAM Credentials |
| Modo no Power BI | Importar |

Pontos de atenção:
- O usuário IAM usado no DSN precisa consultar o Athena, ler o catálogo do Glue e os dados no S3, e **gravar** em `athena-query-results/`.
- As chaves de acesso ficam **somente no DSN do computador**: nunca no repositório, na documentação ou em arquivos de texto.
- O DSN precisa ser criado na versão de **64 bits** do administrador ODBC, a mesma arquitetura do Power BI Desktop.

### 9.2 Tabelas importadas

Todas as 8 tabelas da Curated são importadas para o Power BI.

| Tabela | Nível | Métrica |
|---|---|---|
| `ind1_pagamento_por_fornecedor` | fornecedor | total pago |
| `ind2_recebimento_por_estado` | estado | total recebido (unidades) |
| `ind3_recebimentos_em_dia_por_cidade` | cidade | recebimentos em dia |
| `ind4_recebimentos_em_atraso_por_cidade` | cidade | recebimentos em atraso |
| `ind5_faturamento_por_grupo` | grupo de produto | faturamento |
| `ind6_vendas_por_produto` | produto | vendas, lucro estimado e margem |
| `ind7_vendas_por_pagamento` | forma de pagamento | vendas e ticket médio |
| `ind8_faturamento_por_mes` | ano e mês | faturamento |

### 9.3 Estrutura do dashboard

O dashboard tem três guias:

| Guia | Indicadores | Conteúdo |
|---|---|---|
| **Controle de custos** | ind1, ind2, ind3 e ind4 | Total pago por fornecedor; unidades recebidas por estado; entregas no prazo e com atraso por cidade, com botões para alternar; proporção entre entregas no prazo e com atraso |
| **Controle de vendas** | ind5, ind7 e ind8 | Resultados por forma de pagamento (faturamento, quantidade vendida e ticket médio, com botões); análise por grupo de produto (faturamento, itens vendidos e quantidade de vendas, com botões); evolução mensal do faturamento, com filtro por ano |
| **Desempenho de produtos** | ind6 | Tabela de produtos com vendas, lucro estimado e margem, com busca por produto e código |

**Identidade visual:** página de 1920x1080 (16:9), azul escuro (`#0B1B34`) com moldura dourada (`#C9A961`) e a logo Rocha Analytics no canto superior esquerdo. Textos em branco para contraste.

### 9.3.1 Modelo do relatório

Além das 8 tabelas importadas da Curated, o relatório usa tabelas de apoio criadas no próprio Power BI. Elas não vêm do Athena e não mudam os dados da Curated:

| Tabela de apoio | Função |
|---|---|
| `Medidas auxiliares` | Guarda as medidas DAX do relatório (somas, médias e razões, como itens por venda). |
| `x1 Formas de Pagamento` | Botões que alternam a métrica do indicador 7. |
| `x2 Situação` | Botões "No prazo" e "Com atraso", que alternam entre os indicadores 3 e 4 no mesmo gráfico. |
| `x3 Faturamento por grupos` | Botões que alternam a métrica do indicador 5. |

Os botões são parâmetros de campos ou tabelas soltas ligadas a uma medida, e por isso um mesmo gráfico mostra mais de uma métrica sem duplicar visuais. As porcentagens são exibidas por medidas divididas por 100 com o formato de porcentagem, e o ind5 e o ind6 não são filtrados por ano, porque as tabelas não têm essa coluna.

### 9.4 Atualização dos dados

No modo **Importar**, o Power BI guarda uma cópia dos dados. Depois que a esteira roda (por `push` ou por um dos disparos do EventBridge, de 3 em 3 horas), basta clicar em **Atualizar** para trazer a carga nova. ~~Os três agendamentos diários do cron do GitHub~~ **[REMOVIDO: ver seção 6.1 e `docs/otimizando_automacao.md`]**. Tabelas novas na Curated só aparecem em **Obter dados → Amazon Athena**: o botão Atualizar renova apenas as tabelas já importadas.

O modo Importar foi escolhido porque o Athena cobra pelos dados lidos e os visuais respondem mais rápido: a consulta acontece uma vez por atualização, e não a cada clique no dashboard.

---

## 10. Decisões técnicas

- **Uma pasta por tabela na Trusted:** arquivos soltos fazem o crawler criar colunas de partição indevidas ou uma tabela única vazia.
- **Maiúsculas e minúsculas importam no GitHub Actions:** o servidor é Linux. `SQL` e `sql` são pastas diferentes, ao contrário do Windows.
- **O CTAS falha se a pasta de destino já existir:** por isso o script limpa o prefixo antes de recriar.
- **Validar com números:** cada indicador é conferido contra a soma da tabela de origem, e não apenas contra "a consulta rodou".
- **Avisos em vez de falhas silenciosas:** valores não convertidos aparecem no log como `[AVISO]`.
- **O Power BI lê só a Curated:** a lógica dos indicadores fica no SQL versionado, e não em cálculos soltos no dashboard.
- **Credenciais fora do repositório:** as chaves da esteira ficam nas *Secrets* do GitHub, e as do Power BI ficam apenas no DSN do computador.
- **Dois níveis de CI antes da AWS:** a sintaxe dos scripts Python e a conformidade dos arquivos SQL são validadas sem credenciais, então um erro de código ou de SQL nunca chega a tocar a nuvem.
- **Agendamento pelo EventBridge e fila única:** ~~minutos quebrados no cron do GitHub~~ **[REMOVIDO: o cron do GitHub continuava atrasando]**. O disparo agora vem do Amazon EventBridge (ver `docs/otimizando_automacao.md`), e o `concurrency` continua impedindo duas execuções simultâneas sobre as mesmas pastas do S3.
- **Valores monetários dos indicadores de vendas com 2 casas:** `CAST(... AS DECIMAL(18,2))` no SQL, porque o `total_a_pagar` vem com mais casas decimais (o desconto gera centavos quebrados).
- **Mudança de nome de indicador exige limpeza manual:** ao renomear um `.sql`, a tabela e a pasta antigas continuam no Glue e no S3 e precisam ser apagadas (foi o caso do ind4, de estado para cidade).

### 10.1 Limitações conhecidas

- **`custo` e `venda` da `dim_produto` estão como texto na Trusted.** O `ind6` contorna isso com `TRY_CAST` no próprio SQL. A correção definitiva é incluir essas colunas no `AJUSTES` do `raw_to_trusted.py`.
- **`total_a_pagar` não é arredondado na Trusted.** Os indicadores de vendas arredondam na Curated, e por isso a soma por ano pode diferir de centavos de uma soma feita com cada linha já arredondada.
- **Lucro estimado do `ind6`** usa o custo do cadastro atual, não o custo vigente na data de cada venda.

---

## 11. Controle de status do projeto

| Entregável | Status |
|---|---|
| Estrutura completa do Lakehouse no S3 (Legado, Raw, Trusted, Curated) | Concluído |
| Pipelines de ingestão e transformação | Concluído |
| Particionamento na Trusted | Concluído (12 tabelas por ano e mês; 1 sem coluna de data) |
| Catálogo de dados no Glue | Concluído |
| Quatro indicadores da pós na Curated (ind1 a ind4) | Concluído |
| Indicadores complementares de vendas (ind5 a ind8) | Concluído |
| Scripts SQL de CTAS versionados | Concluído (8 arquivos) |
| CI de Python (sintaxe dos scripts) | Concluído |
| CI de SQL (`validar_sql.py`) | Concluído |
| Esteira CI/CD com disparo agendado | Concluído (EventBridge a cada 3 horas; ~~cron do GitHub 3x ao dia~~ removido em 10/11/2026) |
| Automação do disparo pelo EventBridge | Concluído (ver `docs/otimizando_automacao.md`) |
| Conexão do Power BI com a Curated | Concluído |
| Dashboard no Power BI | Concluído |
| Documentação técnica | Concluído, atualizada em 10/11/2026 |  