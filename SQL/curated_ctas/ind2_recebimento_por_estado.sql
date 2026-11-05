-- =====================================================================
-- INDICADOR 2 - TOTAL DE RECEBIMENTO POR ESTADO
-- Camada: Curated (Trusted -> Curated)
-- Métrica: total_recebimento (soma das unidades recebidas, total_recebido)
-- Dimensão: estado (UF do fornecedor, via JOIN com dim_fornecedor)
-- Validação: 8 estados; soma = 102561 (igual à fato_movimentacao)
-- =====================================================================
CREATE TABLE db_mercadinho_curated.ind2_recebimento_por_estado
WITH (
  format = 'PARQUET',
  external_location = 's3://projeto-mercadinho-erp/curated/ind2_recebimento_por_estado/'
) AS
SELECT
  f.uf AS estado,
  SUM(m.total_recebido) AS total_recebimento
FROM db_mercadinho_trusted.fato_movimentacao m
JOIN db_mercadinho_trusted.dim_fornecedor f
  ON m.id_fornecedor = f.id_fornecedor
GROUP BY f.uf;