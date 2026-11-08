-- =====================================================================
-- INDICADOR 3 - QUANTIDADE DE RECEBIMENTOS EM DIA POR CIDADE
-- Camada: Curated (Trusted -> Curated)
-- Métrica: qtd_recebimentos_em_dia (compras recebidas até a data prevista)
-- Dimensão: cidade (cidade do fornecedor, via JOIN com dim_fornecedor)
-- Regra de "em dia": recebido_em <= previsao_de_entrega
-- Validação: 18 cidades; soma = 2535
-- =====================================================================
CREATE TABLE db_mercadinho_curated.ind3_recebimentos_em_dia_por_cidade
WITH (
  format = 'PARQUET',
  external_location = 's3://projeto-mercadinho-erp/curated/ind3_recebimentos_em_dia_por_cidade/'
) AS
SELECT
  f.cidade,
  COUNT(*) AS qtd_recebimentos_em_dia
FROM db_mercadinho_trusted.fato_movimentacao m
JOIN db_mercadinho_trusted.dim_fornecedor f
  ON m.id_fornecedor = f.id_fornecedor
WHERE m.recebido_em IS NOT NULL
  AND m.recebido_em <= m.previsao_de_entrega
GROUP BY f.cidade;

--== SELECT TESTADO NO ATHENA ANTES DE CRIAR A CTA NO VSCode.
--== RESULTADO SATISFATÓRIO! SQL VALIDADO!