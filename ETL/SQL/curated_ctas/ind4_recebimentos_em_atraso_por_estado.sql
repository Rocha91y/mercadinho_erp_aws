-- =====================================================================
-- INDICADOR 4 - QUANTIDADE DE RECEBIMENTOS EM ATRASO POR ESTADO
-- Camada: Curated (Trusted -> Curated)
-- Métrica: qtd_recebimentos_em_atraso (compras recebidas após a data prevista)
-- Dimensão: estado (UF do fornecedor, via JOIN com dim_fornecedor)
-- Regra de "atraso": recebido_em > previsao_de_entrega
-- Validação: soma = 9603
-- =====================================================================
CREATE TABLE db_mercadinho_curated.ind4_recebimentos_em_atraso_por_estado
WITH (
  format = 'PARQUET',
  external_location = 's3://projeto-mercadinho-erp/curated/ind4_recebimentos_em_atraso_por_estado/'
) AS
SELECT
  f.uf AS estado,
  COUNT(*) AS qtd_recebimentos_em_atraso
FROM db_mercadinho_trusted.fato_movimentacao m
JOIN db_mercadinho_trusted.dim_fornecedor f
  ON m.id_fornecedor = f.id_fornecedor
WHERE m.recebido_em > m.previsao_de_entrega
GROUP BY f.uf;