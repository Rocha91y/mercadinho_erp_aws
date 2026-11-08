-- =====================================================================
-- INDICADOR 5 - FATURAMENTO POR GRUPO DE PRODUTO
-- Camada: Curated (Trusted -> Curated)
-- Métrica: faturamento (soma de total_a_pagar, já com desconto), qtd_itens, qtd_vendas
-- Dimensão: grupo (via fato_vendas -> dim_produto -> dim_grupo)
-- Validação: soma do faturamento = soma de total_a_pagar da fato_vendas
-- =====================================================================
CREATE TABLE db_mercadinho_curated.ind5_faturamento_por_grupo
WITH (
  format = 'PARQUET',
  external_location = 's3://projeto-mercadinho-erp/curated/ind5_faturamento_por_grupo/'
) AS
SELECT
  g.descricao AS grupo,
  CAST(SUM(v.total_a_pagar) AS DECIMAL(18,2)) AS faturamento,
  SUM(v.quantidade) AS qtd_itens,
  COUNT(DISTINCT v.id_venda) AS qtd_vendas
FROM db_mercadinho_trusted.fato_vendas v
JOIN db_mercadinho_trusted.dim_produto p
  ON v.id_produto = p.id_produto
JOIN db_mercadinho_trusted.dim_grupo g
  ON p.id_grupo = g.id_grupo
GROUP BY g.descricao;

--== SELECT TESTADO NO ATHENA ANTES DE CRIAR A CTA NO VSCode.
--== RESULTADO SATISFATÓRIO! SQL VALIDADO!