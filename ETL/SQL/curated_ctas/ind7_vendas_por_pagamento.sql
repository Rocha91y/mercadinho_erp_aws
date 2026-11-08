-- =====================================================================
-- INDICADOR 7 - VENDAS POR FORMA DE PAGAMENTO
-- Camada: Curated (Trusted -> Curated)
-- Métrica: qtd_vendas, faturamento, ticket_medio (faturamento / qtd_vendas)
-- Dimensão: pagamento
-- Validação: soma do faturamento = soma de total_a_pagar da fato_vendas
-- =====================================================================
CREATE TABLE db_mercadinho_curated.ind7_vendas_por_pagamento
WITH (
  format = 'PARQUET',
  external_location = 's3://projeto-mercadinho-erp/curated/ind7_vendas_por_pagamento/'
) AS
SELECT
  v.pagamento,
  COUNT(DISTINCT v.id_venda) AS qtd_vendas,
  CAST(SUM(v.total_a_pagar) AS DECIMAL(18,2)) AS faturamento,
  CAST(SUM(v.total_a_pagar) / COUNT(DISTINCT v.id_venda) AS DECIMAL(18,2)) AS ticket_medio
FROM db_mercadinho_trusted.fato_vendas v
GROUP BY v.pagamento;

--== SELECT TESTADO NO ATHENA ANTES DE CRIAR A CTA NO VSCode.
--== RESULTADO SATISFATÓRIO! SQL VALIDADO!