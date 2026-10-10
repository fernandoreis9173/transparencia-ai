
-- Resumo financeiro geral
-- Fonte: analytics.vw_despesas_analitica
-- Observação: os resultados dependem do dataset carregado.

SELECT
    COUNT(*) AS quantidade_empenhos,
    COUNT(DISTINCT ano_exercicio) AS quantidade_exercicios,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago,
    SUM(vl_pago_rp) AS total_pago_restos_a_pagar,
    COUNT(*) FILTER (
        WHERE situacao_pagamento = 'NAO_PAGO'
    ) AS quantidade_nao_pago,
    COUNT(*) FILTER (
        WHERE situacao_pagamento = 'PAGAMENTO_PARCIAL'
    ) AS quantidade_pagamento_parcial,
    COUNT(*) FILTER (
        WHERE situacao_pagamento = 'PAGO'
    ) AS quantidade_pago,
    COUNT(*) FILTER (
        WHERE liquidado_maior_que_empenhado = TRUE
    ) AS quantidade_anomalias
FROM analytics.vw_despesas_analitica;