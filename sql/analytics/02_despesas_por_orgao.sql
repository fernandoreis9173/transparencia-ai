
-- Despesas agrupadas por órgão
SELECT
    ano_exercicio,
    cod_orgao,
    nome_orgao,
    COUNT(*) AS quantidade_empenhos,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago
FROM analytics.vw_despesas_analitica
GROUP BY
    ano_exercicio,
    cod_orgao,
    nome_orgao
ORDER BY total_empenhado DESC;