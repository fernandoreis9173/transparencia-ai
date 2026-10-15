
from fastapi import APIRouter, Depends, HTTPException, Query

from src.db.connection import get_connection


router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
)


# ============================================================
# CONSULTA AO BANCO DE DADOS
# ============================================================

def consultar(sql: str, params: tuple = ()):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)

                if cursor.description is None:
                    return []

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


# ============================================================
# FILTROS COMPARTILHADOS
# ============================================================

class FiltrosAnalytics:
    def __init__(
        self,
        ano_exercicio: int | None = Query(default=None, ge=2000, le=2100),
        cod_uo: str | None = Query(default=None),
        nome_favorecido: str | None = Query(default=None, max_length=200),
        situacao_pagamento: str | None = Query(default=None),
        apenas_anomalias: bool | None = Query(default=None),
    ):
        self.ano_exercicio = ano_exercicio
        self.cod_uo = cod_uo.strip() if cod_uo else None
        self.nome_favorecido = (
            nome_favorecido.strip()
            if nome_favorecido and nome_favorecido.strip()
            else None
        )
        self.situacao_pagamento = (
            situacao_pagamento.strip().upper()
            if situacao_pagamento
            else None
        )
        self.apenas_anomalias = apenas_anomalias


def montar_filtros(
    filtros: FiltrosAnalytics,
    condicoes_iniciais: list[str] | None = None,
    incluir_filtro_anomalias: bool = True,
):
    """
    Monta condições SQL parametrizadas para os filtros opcionais.

    condicoes_iniciais permite preservar condições próprias de
    endpoints, como exigir uma data ou retornar apenas anomalias.
    """

    condicoes = list(condicoes_iniciais or [])
    params = []

    if filtros.ano_exercicio is not None:
        condicoes.append("ano_exercicio = %s")
        params.append(filtros.ano_exercicio)

    if filtros.cod_uo:
        condicoes.append("cod_uo = %s")
        params.append(filtros.cod_uo)

    if filtros.nome_favorecido:
        condicoes.append("nome_favorecido ILIKE %s")
        params.append(f"%{filtros.nome_favorecido}%")

    if filtros.situacao_pagamento:
        situacoes_validas = {
            "NAO_PAGO",
            "PAGAMENTO_PARCIAL",
            "PAGO",
        }

        if filtros.situacao_pagamento not in situacoes_validas:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Situação inválida. Utilize NAO_PAGO, "
                    "PAGAMENTO_PARCIAL ou PAGO."
                ),
            )

        condicoes.append("situacao_pagamento = %s")
        params.append(filtros.situacao_pagamento)

    if incluir_filtro_anomalias:
        if filtros.apenas_anomalias is True:
            condicoes.append(
                "liquidado_maior_que_empenhado = TRUE"
            )
        elif filtros.apenas_anomalias is False:
            condicoes.append(
                "("
                "liquidado_maior_que_empenhado = FALSE "
                "OR liquidado_maior_que_empenhado IS NULL"
                ")"
            )

    where = (
        " WHERE " + " AND ".join(condicoes)
        if condicoes
        else ""
    )

    return where, tuple(params)


# ============================================================
# RESUMO FINANCEIRO
# ============================================================

@router.get("/resumo")
def obter_resumo(
    filtros: FiltrosAnalytics = Depends(),
):
    where, params = montar_filtros(filtros)

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

        FROM analytics.vw_despesas_analitica
    """ + where + ";"

    resultados = consultar(sql, params)
    return resultados[0]


# ============================================================
# DESPESAS POR ÓRGÃO
# ============================================================

@router.get("/orgaos")
def obter_despesas_por_orgao(
    filtros: FiltrosAnalytics = Depends(),
):
    where, params = montar_filtros(filtros)

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
    """ + where + """
        GROUP BY
            ano_exercicio,
            cod_orgao,
            nome_orgao
        ORDER BY total_empenhado DESC;
    """

    return consultar(sql, params)


# ============================================================
# DESPESAS POR UNIDADE ORÇAMENTÁRIA
# ============================================================

@router.get("/unidades")
def obter_despesas_por_unidade(
    filtros: FiltrosAnalytics = Depends(),
):
    where, params = montar_filtros(filtros)

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
    """ + where + """
        GROUP BY
            ano_exercicio,
            cod_uo,
            nome_uo
        ORDER BY total_empenhado DESC;
    """

    return consultar(sql, params)


# ============================================================
# DESPESAS POR FAVORECIDO
# ============================================================

@router.get("/favorecidos")
def obter_despesas_por_favorecido(
    limite: int = Query(default=10, ge=1, le=100),
    filtros: FiltrosAnalytics = Depends(),
):
    where, params = montar_filtros(filtros)

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
    """ + where + """
        GROUP BY
            ano_exercicio,
            cpf_cnpj_favorecido,
            nome_favorecido
        ORDER BY total_empenhado DESC
        LIMIT %s;
    """

    return consultar(sql, params + (limite,))


# ============================================================
# MAIORES EMPENHOS
# ============================================================

@router.get("/maiores-empenhos")
def obter_maiores_empenhos(
    limite: int = Query(default=20, ge=1, le=100),
    filtros: FiltrosAnalytics = Depends(),
):
    where, params = montar_filtros(filtros)

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
    """ + where + """
        ORDER BY vl_empenhado DESC NULLS LAST
        LIMIT %s;
    """

    return consultar(sql, params + (limite,))


# ============================================================
# EVOLUÇÃO MENSAL
# ============================================================

@router.get("/evolucao-mensal")
def obter_evolucao_mensal(
    filtros: FiltrosAnalytics = Depends(),
):
    where, params = montar_filtros(
        filtros,
        condicoes_iniciais=[
            "data_registro_empenho IS NOT NULL"
        ],
    )

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
    """ + where + """
        GROUP BY
            ano_exercicio,
            DATE_TRUNC('month', data_registro_empenho)::date
        ORDER BY mes;
    """

    return consultar(sql, params)


# ============================================================
# SITUAÇÃO DOS PAGAMENTOS
# ============================================================

@router.get("/situacao-pagamento")
def obter_situacao_pagamento(
    filtros: FiltrosAnalytics = Depends(),
):
    where, params = montar_filtros(filtros)

    sql = """
        SELECT
            situacao_pagamento,
            COUNT(*) AS quantidade_empenhos,
            COALESCE(SUM(vl_empenhado), 0) AS total_empenhado,
            COALESCE(SUM(vl_liquidado), 0) AS total_liquidado,
            COALESCE(SUM(vl_pago), 0) AS total_pago
        FROM analytics.vw_despesas_analitica
    """ + where + """
        GROUP BY situacao_pagamento
        ORDER BY quantidade_empenhos DESC;
    """

    return consultar(sql, params)


# ============================================================
# ANOMALIAS / REGISTROS PARA VERIFICAÇÃO
# ============================================================

@router.get("/anomalias")
def obter_anomalias(
    filtros: FiltrosAnalytics = Depends(),
):
    where, params = montar_filtros(
        filtros,
        condicoes_iniciais=[
            "liquidado_maior_que_empenhado = TRUE"
        ],
        incluir_filtro_anomalias=False,
    )

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
    """ + where + """
        ORDER BY diferenca_liquidado_empenhado DESC;
    """

    return consultar(sql, params)


# ============================================================
# DETALHES DE UM EMPENHO
# ============================================================

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
