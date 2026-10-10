
-- Despesas por unidade orçamentária
SELECT
    ano_exercicio,
    cod_orgao,
    nome_orgao,
    cod_uo,
    nome_uo,
    COUNT(*) AS quantidade_empenhos,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago
FROM analytics.vw_despesas_analitica
GROUP BY
    ano_exercicio,
    cod_orgao,
    nome_orgao,
    cod_uo,
    nome_uo
ORDER BY total_empenhado DESC;