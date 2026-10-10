
-- Anomalias financeiras para investigação
-- Os valores originais da fonte não são alterados.

SELECT
    ano_exercicio,
    num_empenho,
    data_registro_empenho,
    nome_orgao,
    nome_uo,
    cpf_cnpj_favorecido,
    nome_favorecido,
    vl_empenhado,
    vl_liquidado,
    vl_pago,
    vl_liquidado - vl_empenhado AS diferenca_liquidado_empenhado,
    percentual_liquidado,
    liquidado_maior_que_empenhado
FROM analytics.vw_despesas_analitica
WHERE liquidado_maior_que_empenhado = TRUE
ORDER BY
    diferenca_liquidado_empenhado DESC;
