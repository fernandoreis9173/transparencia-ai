-- Distribuição por situação de pagamento
SELECT
    situacao_pagamento,
    COUNT(*) AS quantidade_empenhos,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago
FROM analytics.vw_despesas_analitica
GROUP BY situacao_pagamento
ORDER BY quantidade_empenhos DESC;