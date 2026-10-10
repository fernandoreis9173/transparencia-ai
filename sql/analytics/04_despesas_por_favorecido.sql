
-- Dez favorecidos com maior valor empenhado
SELECT
    ano_exercicio,
    cpf_cnpj_favorecido,
    nome_favorecido,
    COUNT(*) AS quantidade_empenhos,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago
FROM analytics.vw_despesas_analitica
GROUP BY
    ano_exercicio,
    cpf_cnpj_favorecido,
    nome_favorecido
ORDER BY total_empenhado DESC
LIMIT 10;