-- Maiores empenhos individuais
SELECT
    ano_exercicio,
    num_empenho,
    data_registro_empenho,
    nome_orgao,
    nome_uo,
    nome_favorecido,
    vl_empenhado,
    vl_liquidado,
    vl_pago,
    liquidado_maior_que_empenhado
FROM analytics.vw_despesas_analitica
ORDER BY vl_empenhado DESC NULLS LAST
LIMIT 20;