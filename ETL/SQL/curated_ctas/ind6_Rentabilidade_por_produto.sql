-- =====================================================================
-- INDICADOR 6 - VENDAS E RENTABILIDADE POR PRODUTO
-- Camada: Curated (Trusted -> Curated)
-- Métrica: qtd_itens, faturamento, lucro_estimado, margem_pct
-- Dimensão: produto (fato_vendas -> dim_produto)
-- Obs.: custo e venda vêm como texto na dim_produto, por isso o TRY_CAST
-- Validação: soma do faturamento = soma de total_a_pagar da fato_vendas
-- =====================================================================
CREATE TABLE db_mercadinho_curated.ind6_vendas_por_produto
WITH (
  format = 'PARQUET',
  external_location = 's3://projeto-mercadinho-erp/curated/ind6_vendas_por_produto/'
) AS
WITH prod AS (
  SELECT
    id_produto,
    TRY_CAST(REPLACE(custo, ',', '.') AS DOUBLE) AS custo,
    TRY_CAST(REPLACE(venda, ',', '.') AS DOUBLE) AS venda
  FROM db_mercadinho_trusted.dim_produto
)
SELECT
  v.id_produto,
  v.descricao AS produto,
  p.custo,
  p.venda AS preco_venda,
  ROUND((p.venda - p.custo) / NULLIF(p.venda, 0) * 100, 2) AS margem_pct,
  SUM(v.quantidade) AS qtd_itens,
  CAST(SUM(v.total_a_pagar) AS DECIMAL(18,2)) AS faturamento,
  CAST(SUM(v.total_a_pagar) - SUM(v.quantidade * p.custo) AS DECIMAL(18,2)) AS lucro_estimado,
  COUNT(DISTINCT v.id_venda) AS qtd_vendas
FROM db_mercadinho_trusted.fato_vendas v
JOIN prod p
  ON v.id_produto = p.id_produto
GROUP BY v.id_produto, v.descricao, p.custo, p.venda;

--== SELECT TESTADO NO ATHENA ANTES DE CRIAR A CTA NO VSCode.
--== CORRIGIDO CASAS DECIMAIS QUE APARECIAM COM MAIS DE 2.
--== RESULTADO SATISFATÓRIO! SQL VALIDADO!