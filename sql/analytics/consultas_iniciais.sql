-- resumo financeiro
SELECT
    COUNT(*) AS quantidade_empenhos,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago,
    SUM(vl_pago_rp) AS total_pago_rp
FROM analytics.vw_despesas;

-- despesas por órgão
SELECT
    cod_orgao,
    nome_orgao,
    COUNT(*) AS quantidade_empenhos,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago
FROM analytics.vw_despesas
GROUP BY
    cod_orgao,
    nome_orgao
ORDER BY
    total_empenhado DESC;

-- despesas por unidade orçamentária
SELECT
    cod_uo,
    nome_uo,
    COUNT(*) AS quantidade_empenhos,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago
FROM analytics.vw_despesas
GROUP BY
    cod_uo,
    nome_uo
ORDER BY
    total_empenhado DESC;

-- maiores favorecidos
SELECT
    cpf_cnpj_favorecido,
    nome_favorecido,
    COUNT(*) AS quantidade_empenhos,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago
FROM analytics.vw_despesas
GROUP BY
    cpf_cnpj_favorecido,
    nome_favorecido
ORDER BY
    total_empenhado DESC
LIMIT 10;

-- maiores empenhos individuais
SELECT
    num_empenho,
    data_registro_empenho,
    nome_orgao,
    nome_uo,
    nome_favorecido,
    nome_acao,
    vl_empenhado,
    vl_liquidado,
    vl_pago
FROM analytics.vw_despesas
ORDER BY
    vl_empenhado DESC
LIMIT 10;

-- evolução mensal
SELECT
    DATE_TRUNC('month', data_registro_empenho)::date AS mes,
    COUNT(*) AS quantidade_empenhos,
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago
FROM analytics.vw_despesas
GROUP BY
    DATE_TRUNC('month', data_registro_empenho)
ORDER BY
    mes;

-- empenhado × liquidado × pago
SELECT
    SUM(vl_empenhado) AS total_empenhado,
    SUM(vl_liquidado) AS total_liquidado,
    SUM(vl_pago) AS total_pago,
    SUM(vl_empenhado - vl_pago) AS empenhado_nao_pago
FROM analytics.vw_despesas;

-- anomalias financeiras
SELECT
    num_empenho,
    nome_favorecido,
    vl_empenhado,
    vl_liquidado,
    vl_liquidado - vl_empenhado AS diferenca
FROM analytics.vw_despesas
WHERE liquidado_maior_que_empenhado = TRUE
ORDER BY
    diferenca DESC;

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

-- E uma consulta muito importante para a IA
SELECT
    num_empenho,
    ano_exercicio,
    nome_orgao,
    nome_uo,
    nome_favorecido,
    cpf_cnpj_favorecido,
    nome_funcao,
    nome_subfuncao,
    nome_programa,
    nome_acao,
    nome_tipo_licitacao,
    num_processo,
    data_registro_empenho,
    vl_empenhado_inicial,
    vl_empenhado,
    vl_reforco,
    vl_anulacao,
    vl_liquidado,
    vl_pago,
    vl_pago_rp,
    indicador_restos,
    liquidado_maior_que_empenhado
FROM analytics.vw_despesas
WHERE num_empenho = '2025NE00662';