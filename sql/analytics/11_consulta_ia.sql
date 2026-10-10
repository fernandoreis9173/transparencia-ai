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