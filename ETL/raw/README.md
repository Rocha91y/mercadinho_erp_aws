# Camada Trusted

Transforma a base mestra (xlsx) em tabelas padronizadas no formato **Parquet**, separadas em dimensões e fatos, e envia para o S3.

## O que o script faz

`raw_to_trusted.py`, em ordem:

1. Lê cada guia do xlsx sem cabeçalho.
2. Detecta automaticamente a linha do cabeçalho (primeira linha bem preenchida).
3. Usa essa linha como nomes das colunas e descarta o que vem acima dela.
4. Padroniza os nomes das colunas: minúsculas, sem acento, `_` no lugar de espaço, hífen e `/`.
5. Remove linhas e colunas totalmente vazias e resolve nomes de colunas repetidos.
6. Grava um Parquet por guia e envia para o S3.

## Entrada

`1base_mestra/Base_de_dados_mercadinho-Corrigida.xlsx`

## Saída

Uma pasta por tabela, com o Parquet dentro (o crawler do Glue exige esse formato):

```
s3://projeto-mercadinho-erp/trusted/
|__dimensoes/<dim_nome>/<dim_nome>.parquet
|__fatos/<fato_nome>/<fato_nome>.parquet
```

## Classificação das guias

| Tipo | Guias |
|---|---|
| Dimensões (`dim_`) | PRODUTO, GRUPO, FORNECEDOR, CLIENTES CONTA, CADASTRO COLABORADORES, TABELA ENCARGOS |
| Fatos (`fato_`) | VENDAS, ESTOQUE, MOVIMENTACAO, HISTÓRICO FINANCEIRO, FOLHA PAGAMENTO, GASTOS FIXOS, VALORES |
| Ignoradas | FORMULAS (anotação, não é tabela de dados) |

## Execução

Roda automaticamente no pipeline (`.github/workflows`), depois do Legado e da Raw, a cada push na `main`.

Dependências: `boto3`, `pandas`, `openpyxl`, `unidecode`, `pyarrow`.

## Pendências

- Hoje o xlsx é lido da pasta do repositório; o desenho da arquitetura prevê ler da camada Raw no S3.
- Todas as colunas são gravadas como texto. A conversão de tipos (datas, números) ainda será feita.