-- =====================================================================
-- INDICADOR 8 - FATURAMENTO POR MÊS
-- Camada: Curated (Trusted -> Curated)
-- Métrica: faturamento, qtd_vendas, qtd_itens
-- Dimensão: ano e mês (colunas de partição da fato_vendas)
-- Validação: soma do faturamento = soma de total_a_pagar da fato_vendas
-- =====================================================================
CREATE TABLE db_mercadinho_curated.ind8_faturamento_por_mes
WITH (
  format = 'PARQUET',
  external_location = 's3://projeto-mercadinho-erp/curated/ind8_faturamento_por_mes/'
) AS
SELECT
  v.ano,
  v.mes,
  CAST(SUM(v.total_a_pagar) AS DECIMAL(18,2)) AS faturamento,
  COUNT(DISTINCT v.id_venda) AS qtd_vendas,
  SUM(v.quantidade) AS qtd_itens
FROM db_mercadinho_trusted.fato_vendas v
GROUP BY v.ano, v.mes;

--== SELECT TESTADO NO ATHENA ANTES DE CRIAR A CTA NO VSCode.
--== RESULTADO SATISFATÓRIO! SQL VALIDADO!