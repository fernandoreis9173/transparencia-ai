-- Evolução mensal dos valores
SELECT
    ano_exercicio,
    DATE_TRUNC('month', data_registro_empenho)::date AS mes,
    COUNT(*) AS quantidade_empenhos,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago
FROM analytics.vw_despesas_analitica
WHERE data_registro_empenho IS NOT NULL
GROUP BY
    ano_exercicio,
    DATE_TRUNC('month', data_registro_empenho)::date
ORDER BY mes;