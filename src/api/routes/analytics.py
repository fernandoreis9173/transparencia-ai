
from fastapi import APIRouter, HTTPException, Query

from src.db.connection import get_connection

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
)


def consultar(sql: str, params: tuple = ()):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)

                colunas = [
                    item.name
                    for item in cursor.description
                ]

                return [
                    dict(zip(colunas, linha))
                    for linha in cursor.fetchall()
                ]

    except Exception as erro:
        print(f"Erro na consulta analítica: {erro}")
        raise HTTPException(
            status_code=500,
            detail="Não foi possível consultar os dados analíticos.",
        ) from erro


@router.get("/resumo")
def obter_resumo():
    sql = """
        SELECT
            COUNT(*) AS quantidade_empenhos,
            COUNT(DISTINCT ano_exercicio) AS quantidade_exercicios,
            COALESCE(SUM(vl_empenhado), 0) AS total_empenhado,
            COALESCE(SUM(vl_liquidado), 0) AS total_liquidado,
            COALESCE(SUM(vl_pago), 0) AS total_pago,
            COALESCE(SUM(vl_pago_rp), 0) AS total_pago_restos_a_pagar,
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
    """

    return consultar(sql)[0]


@router.get("/orgaos")
def obter_despesas_por_orgao():
    sql = """
        SELECT
            ano_exercicio,
            cod_orgao,
            nome_orgao,
            COUNT(*) AS quantidade_empenhos,
            COALESCE(SUM(vl_empenhado), 0) AS total_empenhado,
            COALESCE(SUM(vl_liquidado), 0) AS total_liquidado,
            COALESCE(SUM(vl_pago), 0) AS total_pago
        FROM analytics.vw_despesas_analitica
        GROUP BY ano_exercicio, cod_orgao, nome_orgao
        ORDER BY total_empenhado DESC;
    """

    return consultar(sql)


@router.get("/unidades")
def obter_despesas_por_unidade():
    sql = """
        SELECT
            ano_exercicio,
            cod_uo,
            nome_uo,
            COUNT(*) AS quantidade_empenhos,
            COALESCE(SUM(vl_empenhado), 0) AS total_empenhado,
            COALESCE(SUM(vl_liquidado), 0) AS total_liquidado,
            COALESCE(SUM(vl_pago), 0) AS total_pago
        FROM analytics.vw_despesas_analitica
        GROUP BY ano_exercicio, cod_uo, nome_uo
        ORDER BY total_empenhado DESC;
    """

    return consultar(sql)


@router.get("/favorecidos")
def obter_despesas_por_favorecido(
    limite: int = Query(default=10, ge=1, le=100)
):
    sql = """
        SELECT
            ano_exercicio,
            cpf_cnpj_favorecido,
            nome_favorecido,
            COUNT(*) AS quantidade_empenhos,
            COALESCE(SUM(vl_empenhado), 0) AS total_empenhado,
            COALESCE(SUM(vl_liquidado), 0) AS total_liquidado,
            COALESCE(SUM(vl_pago), 0) AS total_pago
        FROM analytics.vw_despesas_analitica
        GROUP BY
            ano_exercicio,
            cpf_cnpj_favorecido,
            nome_favorecido
        ORDER BY total_empenhado DESC
        LIMIT %s;
    """

    return consultar(sql, (limite,))


@router.get("/maiores-empenhos")
def obter_maiores_empenhos(
    limite: int = Query(default=20, ge=1, le=100)
):
    sql = """
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
        LIMIT %s;
    """

    return consultar(sql, (limite,))


@router.get("/evolucao-mensal")
def obter_evolucao_mensal():
    sql = """
        SELECT
            ano_exercicio,
            DATE_TRUNC(
                'month', data_registro_empenho
            )::date AS mes,
            COUNT(*) AS quantidade_empenhos,
            COALESCE(SUM(vl_empenhado), 0) AS total_empenhado,
            COALESCE(SUM(vl_liquidado), 0) AS total_liquidado,
            COALESCE(SUM(vl_pago), 0) AS total_pago
        FROM analytics.vw_despesas_analitica
        WHERE data_registro_empenho IS NOT NULL
        GROUP BY
            ano_exercicio,
            DATE_TRUNC('month', data_registro_empenho)::date
        ORDER BY mes;
    """

    return consultar(sql)


@router.get("/situacao-pagamento")
def obter_situacao_pagamento():
    sql = """
        SELECT
            situacao_pagamento,
            COUNT(*) AS quantidade_empenhos,
            COALESCE(SUM(vl_empenhado), 0) AS total_empenhado,
            COALESCE(SUM(vl_liquidado), 0) AS total_liquidado,
            COALESCE(SUM(vl_pago), 0) AS total_pago
        FROM analytics.vw_despesas_analitica
        GROUP BY situacao_pagamento
        ORDER BY quantidade_empenhos DESC;
    """

    return consultar(sql)


@router.get("/anomalias")
def obter_anomalias():
    sql = """
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
            vl_liquidado - vl_empenhado
                AS diferenca_liquidado_empenhado,
            percentual_liquidado,
            liquidado_maior_que_empenhado
        FROM analytics.vw_despesas_analitica
        WHERE liquidado_maior_que_empenhado = TRUE
        ORDER BY diferenca_liquidado_empenhado DESC;
    """

    return consultar(sql)


@router.get("/empenhos/{numero}")
def obter_detalhes_empenho(numero: str):
    sql = """
        SELECT *
        FROM analytics.vw_despesas_analitica
        WHERE num_empenho = %s
        LIMIT 1;
    """

    resultados = consultar(sql, (numero,))

    if not resultados:
        raise HTTPException(
            status_code=404,
            detail="Empenho não encontrado.",
        )

    return resultados[0]
