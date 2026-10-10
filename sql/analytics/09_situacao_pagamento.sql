    -- distribuição por situação de pagamento
SELECT
    CASE
        WHEN vl_pago = 0 THEN 'Não pago'
        WHEN vl_pago < vl_liquidado THEN 'Pagamento parcial'
        WHEN vl_pago >= vl_liquidado THEN 'Pago'
        ELSE 'Não classificado'
    END AS situacao_pagamento,
    COUNT(*) AS quantidade_empenhos,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago
FROM analytics.vw_despesas
GROUP BY
    CASE
        WHEN vl_pago = 0 THEN 'Não pago'
        WHEN vl_pago < vl_liquidado THEN 'Pagamento parcial'
        WHEN vl_pago >= vl_liquidado THEN 'Pago'
        ELSE 'Não classificado'
    END
ORDER BY
    total_empenhado DESC;