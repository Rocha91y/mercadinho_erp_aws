-- =====================================================================
-- INDICADOR 4 - QUANTIDADE DE RECEBIMENTOS EM ATRASO POR CIDADE
-- Camada: Curated (Trusted -> Curated)
-- Métrica: qtd_recebimentos_em_atraso (compras recebidas após a data prevista)
-- Dimensão: cidade (cidade do fornecedor, via JOIN com dim_fornecedor)
-- Regra de "atraso": recebido_em > previsao_de_entrega
-- Validação: soma = 9603
-- =====================================================================
CREATE TABLE db_mercadinho_curated.ind4_recebimentos_em_atraso_por_cidade
WITH (
  format = 'PARQUET',
  external_location = 's3://projeto-mercadinho-erp/curated/ind4_recebimentos_em_atraso_por_cidade/'
) AS
SELECT
  f.cidade,
  COUNT(*) AS qtd_recebimentos_em_atraso
FROM db_mercadinho_trusted.fato_movimentacao m
JOIN db_mercadinho_trusted.dim_fornecedor f
  ON m.id_fornecedor = f.id_fornecedor
WHERE m.recebido_em IS NOT NULL
  AND m.recebido_em > m.previsao_de_entrega
GROUP BY f.cidade;

--== SELECT TESTADO NO ATHENA ANTES DE CRIAR A CTA NO VSCode.
--== AJUSTADO PARA CIDADES AO INVÉS DE ESTADOS, POIS O INDICADOR 3 É POR CIDADE.
--== RESULTADO SATISFATÓRIO! SQL VALIDADO!