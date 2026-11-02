Aqui está uma estruturação profissional, técnica e elegante para o seu projeto, ideal para o `README.md` do seu repositório no GitHub ou para a apresentação ao professor:

---

# 🚀 Projeto Integrado: Arquitetura de Dados End-to-End para Varejo (Mercadinho ERP & AWS Lakehouse)

## 📌 Visão Geral do Projeto

Este projeto consiste em uma solução completa de **Engenharia de Dados e Gestão de Dados**, unindo conceitos avançados de modelagem relacional, automação de processos, engenharia de software e computação em nuvem (AWS). A iniciativa simula o ecossistema tecnológico completo de uma operação de comércio varejista de médio porte, cobrindo desde a geração transacional dos dados até camadas analíticas modernas.

---

## 🏗️ Arquitetura e Tecnologias Utilizadas

* **Origem e Modelagem:** Excel Avançado (Base Mestra com regras de negócio e simulação temporal).
* **Armazenamento e Camadas (Lakehouse):** Amazon S3 (AWS) estruturado em arquitetura *Medallion* (`Legado`, `Raw`, `Trusted`, `Curated`, `Athena-Query-Results`).
* **Banco de Dados Relacional & Transacional:** PostgreSQL (hospedado no Supabase) com restrições de integridade, chaves estrangeiras (`references`), chaves primárias e regras de negócio via SQL.
* **Automação e Orquestração:** Python (`boto3`, `pandas`, `tkinter`), Git e **GitHub Actions**.

---

## 🔄 Pipeline e Fluxo de Dados

### 1. Camada de Origem e Ingestão (Excel & AWS S3 - `Legado`)

* **Simulação de Negócio:** Desenvolvimento de uma base de dados robusta no Excel (*Projeto - Mercadinho_ERP - Base_Mestra*) simulando o dia a dia de um varejo (faturamento, despesas, quantidade de funcionários, vendas e operações) de forma gradual até o período atual.
* **Backup e Versionamento na Nuvem:** O arquivo original é capturado de forma automatizada e enviado diretamente para a pasta `Legado/` em um bucket do **Amazon S3**, garantindo a imutabilidade do dado cru de origem.

### 2. Processamento e Carga no Banco de Dados Relacional (Supabase / PostgreSQL)

* **Extração para CSV:** As abas do Excel são exportadas de forma estruturada para a pasta de arquivos brutos.
* **Modelagem Relacional (SQL):** Criação de tabelas no Supabase aplicando rigor de engenharia de dados:
* Uso de chaves primárias e estrangeiras (`references`) para garantir integridade referencial.
* Automações e cálculos de impacto no estoque (reduções/aumentos baseados em vendas e recebimentos).


* **Limpeza e Tratamento com Python:** Antes da carga no banco, os dados dos CSVs passam por um pipeline de higienização:
* Remoção de colunas calculadas nativamente pelo banco.
* Remoção de acentuações e padronização de cabeçalhos para letras minúsculas.
* Conversão de formatos de data de `DD-MM-AAAA` para o padrão ISO (`AAAA-MM-DD`).
* Tratamento de separadores decimais financeiros (substituição de vírgula por ponto).



### 3. Aplicação Operacional (Executável Python com Tkinter)

* **Simulação de Reposição de Estoque:** Desenvolvimento de uma interface gráfica leve utilizando **Tkinter** para gerar um executável voltado ao gestor de logística.
* **Fluxo de Compras:** O programa verifica produtos com estoque abaixo do mínimo (calculado via medidas e médias inspiradas em DAX/SQL), permitindo ao gestor selecionar os itens necessários e disparar um novo pedido de compra diretamente para a base de dados no Supabase (com status inicial pendente).

### 4. Automação de Fornecedores e Logística (GitHub Actions)

* **Simulação de Supply Chain:** Um script em Python executado diariamente via **GitHub Actions** consome o banco de dados PostgreSQL.
* **Regras de Faturamento e Prazos:**
* Identifica pedidos não faturados e atribui uma data aleatória de faturamento entre 2 a 5 dias.
* Calcula valores de frete e prazos de entrega estimados.
* Simula a variabilidade logística gerando cenários de entregas antecipadas, pontuais ou com **tendências de atraso** em relação à previsão.



### 5. Simulação de Vendas Automatizadas

* **Geração Transacional de Caixa:** Um rotina automatizada lança vendas diariamente respeitando os horários comerciais reais da operação:
* **Segunda a Sexta-feira:** das 08:00 às 17:59 (exceto feriados nacionais).
* **Sábados:** das 08:00 às 11:59 (exceto feriados nacionais).



---

## ☁️ Evolução para Cloud & Lakehouse (AWS)

O projeto foi expandido para incorporar a infraestrutura da **AWS**, estruturando o armazenamento S3 nas seguintes camadas analíticas:

* **`Legado/`**: Repositório imutável dos arquivos `.xlsx` originais de origem.
* **`Raw/`**: Dados brutos convertidos em CSVs sem transformações complexas.
* **`Trusted/`**: Dados limpos, tipados e convertidos para o formato otimizado **Parquet**.
* **`Curated/`**: Visões analíticas refinadas e prontas para consumo por ferramentas de BI e pipelines de **MLOps**.
* **`Athena-Query-Results/`**: Diretório dedicado ao armazenamento de metadados e resultados de consultas via Amazon Athena.
