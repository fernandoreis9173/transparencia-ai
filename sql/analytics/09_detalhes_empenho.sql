
-- Detalhes de um empenho específico
-- Substitua o número pelo empenho desejado.

SELECT
    ano_exercicio,
    num_empenho,
    num_processo,
    data_registro_empenho,
    nome_orgao,
    cod_uo,
    nome_uo,
    cpf_cnpj_favorecido,
    nome_favorecido,
    nome_funcao,
    nome_subfuncao,
    nome_programa,
    nome_acao,
    cod_elemento,
    cod_item,
    nome_tipo_licitacao,
    indicador_restos,
    vl_empenhado_inicial,
    vl_empenhado,
    vl_reforco,
    vl_anulacao,
    vl_liquidado,
    vl_pago,
    vl_pago_rp,
    valor_liquidado_nao_pago,
    valor_empenhado_nao_pago,
    percentual_liquidado,
    percentual_pago,
    situacao_pagamento,
    liquidado_maior_que_empenhado
FROM analytics.vw_despesas_analitica
WHERE num_empenho = '2025NE40343';
