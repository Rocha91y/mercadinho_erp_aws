-- =====================================================================
-- INDICADOR 1 - TOTAL DE PAGAMENTO POR FORNECEDOR
-- Camada: Curated (Trusted -> Curated)
-- Métrica: total_pagamento (soma do custo_total das compras)
-- Dimensão: fornecedor
-- Validação: 32 linhas (um por fornecedor com compras)
-- =====================================================================
CREATE TABLE db_mercadinho_curated.ind1_pagamento_por_fornecedor
WITH (
  format = 'PARQUET',
  external_location = 's3://projeto-mercadinho-erp/curated/ind1_pagamento_por_fornecedor/'
) AS
SELECT
  id_fornecedor,
  fornecedor,
  ROUND(SUM(custo_total), 2) AS total_pagamento
FROM db_mercadinho_trusted.fato_movimentacao
GROUP BY id_fornecedor, fornecedor;

--== SELECT TESTADO NO ATHENA ANTES DE CRIAR A CTA NO VSCode.
--== RESULTADO SATISFATÓRIO! SQL VALIDADO!