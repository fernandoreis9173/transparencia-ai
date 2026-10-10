-- análise por ação
SELECT
    cod_acao,
    nome_acao,
    COUNT(*) AS quantidade_empenhos,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago
FROM analytics.vw_despesas
GROUP BY
    cod_acao,
    nome_acao
ORDER BY
    total_empenhado DESC;