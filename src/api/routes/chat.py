
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.db.connection import get_connection
from src.api.services.ai_service import (
    classificar_pergunta,
    gerar_resposta,
)


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat com IA"],
)


class FiltrosChat(BaseModel):
    ano_exercicio: int | None = Field(
        default=None, ge=2000, le=2100
    )
    cod_uo: str | None = Field(default=None, max_length=30)
    nome_favorecido: str | None = Field(
        default=None, max_length=200
    )
    situacao_pagamento: (
        Literal["NAO_PAGO", "PAGAMENTO_PARCIAL", "PAGO"] | None
    ) = None
    apenas_anomalias: bool | None = None


class PerguntaChat(BaseModel):
    pergunta: str = Field(min_length=2, max_length=1000)
    filtros: FiltrosChat = Field(default_factory=FiltrosChat)


def montar_where(
    filtros: FiltrosChat,
    intencao: str,
) -> tuple[str, tuple]:
    condicoes = []
    parametros = []

    if filtros.ano_exercicio is not None:
        condicoes.append("ano_exercicio = %s")
        parametros.append(filtros.ano_exercicio)

    if filtros.cod_uo and filtros.cod_uo.strip():
        condicoes.append("cod_uo = %s")
        parametros.append(filtros.cod_uo.strip())

    if filtros.nome_favorecido and filtros.nome_favorecido.strip():
        condicoes.append("nome_favorecido ILIKE %s")
        parametros.append(
            f"%{filtros.nome_favorecido.strip()}%"
        )

    if filtros.situacao_pagamento:
        condicoes.append("situacao_pagamento = %s")
        parametros.append(filtros.situacao_pagamento)

    if intencao == "anomalias":
        condicoes.append(
            "liquidado_maior_que_empenhado = TRUE"
        )
    elif filtros.apenas_anomalias is True:
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

    return where, tuple(parametros)


def executar_consulta(
    intencao: str,
    filtros: FiltrosChat,
) -> list[dict]:
    """
    Seleciona exclusivamente SQL definido neste arquivo.
    Nenhum SQL é gerado pelo modelo de IA.
    """
    where, parametros = montar_where(filtros, intencao)

    consultas = {
        "resumo": """
            SELECT
                COUNT(*) AS quantidade_empenhos,
                COUNT(DISTINCT ano_exercicio)
                    AS quantidade_exercicios,
                COALESCE(SUM(vl_empenhado), 0)
                    AS total_empenhado,
                COALESCE(SUM(vl_liquidado), 0)
                    AS total_liquidado,
                COALESCE(SUM(vl_pago), 0)
                    AS total_pago,
                COALESCE(SUM(vl_pago_rp), 0)
                    AS total_pago_restos_a_pagar,
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
        """,

        "top_favorecidos": """
            SELECT
                nome_favorecido,
                COUNT(*) AS quantidade_empenhos,
                COALESCE(SUM(vl_empenhado), 0)
                    AS total_empenhado,
                COALESCE(SUM(vl_liquidado), 0)
                    AS total_liquidado,
                COALESCE(SUM(vl_pago), 0)
                    AS total_pago
            FROM analytics.vw_despesas_analitica
        """,

        "situacao_pagamento": """
            SELECT
                situacao_pagamento,
                COUNT(*) AS quantidade_empenhos,
                COALESCE(SUM(vl_empenhado), 0)
                    AS total_empenhado,
                COALESCE(SUM(vl_liquidado), 0)
                    AS total_liquidado,
                COALESCE(SUM(vl_pago), 0)
                    AS total_pago
            FROM analytics.vw_despesas_analitica
        """,

        "anomalias": """
            SELECT
                num_empenho,
                data_registro_empenho,
                nome_orgao,
                nome_uo,
                nome_favorecido,
                vl_empenhado,
                vl_liquidado,
                vl_pago,
                vl_liquidado - vl_empenhado
                    AS diferenca_liquidado_empenhado
            FROM analytics.vw_despesas_analitica
        """,

        "maiores_empenhos": """
            SELECT
                num_empenho,
                data_registro_empenho,
                nome_orgao,
                nome_uo,
                nome_favorecido,
                vl_empenhado,
                vl_liquidado,
                vl_pago
            FROM analytics.vw_despesas_analitica
        """,

        "evolucao_mensal": """
            SELECT
                DATE_TRUNC(
                    'month', data_registro_empenho
                )::date AS mes,
                COUNT(*) AS quantidade_empenhos,
                COALESCE(SUM(vl_empenhado), 0)
                    AS total_empenhado,
                COALESCE(SUM(vl_liquidado), 0)
                    AS total_liquidado,
                COALESCE(SUM(vl_pago), 0)
                    AS total_pago
            FROM analytics.vw_despesas_analitica
        """,

        "unidades": """
            SELECT
                cod_uo,
                nome_uo,
                COUNT(*) AS quantidade_empenhos,
                COALESCE(SUM(vl_empenhado), 0)
                    AS total_empenhado,
                COALESCE(SUM(vl_liquidado), 0)
                    AS total_liquidado,
                COALESCE(SUM(vl_pago), 0)
                    AS total_pago
            FROM analytics.vw_despesas_analitica
        """,
    }

    sql = consultas.get(intencao)

    if sql is None:
        raise HTTPException(
            status_code=400,
            detail="Tipo de consulta não permitido.",
        )

    if intencao == "evolucao_mensal":
        where, parametros = montar_where(filtros, intencao)
        where = (
            where + " AND data_registro_empenho IS NOT NULL"
            if where
            else " WHERE data_registro_empenho IS NOT NULL"
        )

    sql += where

    if intencao == "top_favorecidos":
        sql += """
            GROUP BY nome_favorecido
            ORDER BY total_empenhado DESC
            LIMIT 10
        """
    elif intencao == "situacao_pagamento":
        sql += """
            GROUP BY situacao_pagamento
            ORDER BY quantidade_empenhos DESC
        """
    elif intencao == "anomalias":
        sql += """
            ORDER BY diferenca_liquidado_empenhado DESC
            LIMIT 20
        """
    elif intencao == "maiores_empenhos":
        sql += """
            ORDER BY vl_empenhado DESC NULLS LAST
            LIMIT 10
        """
    elif intencao == "evolucao_mensal":
        sql += """
            GROUP BY DATE_TRUNC(
                'month', data_registro_empenho
            )::date
            ORDER BY mes
        """
    elif intencao == "unidades":
        sql += """
            GROUP BY cod_uo, nome_uo
            ORDER BY total_empenhado DESC
            LIMIT 10
        """

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, parametros)

                if cursor.description is None:
                    return []

                colunas = [
                    coluna.name
                    for coluna in cursor.description
                ]

                return [
                    dict(zip(colunas, linha))
                    for linha in cursor.fetchall()
                ]

    except Exception as erro:
        print(f"Erro na consulta do chat: {erro}")

        raise HTTPException(
            status_code=500,
            detail="Não foi possível consultar os dados do chat.",
        ) from erro


@router.post("/perguntar")
def perguntar(payload: PerguntaChat):
    pergunta = payload.pergunta.strip()

    if len(pergunta) < 2:
        raise HTTPException(
            status_code=422,
            detail="Digite uma pergunta válida.",
        )

    intencao = classificar_pergunta(pergunta)

    dados = executar_consulta(
        intencao=intencao,
        filtros=payload.filtros,
    )

    filtros_aplicados = payload.filtros.model_dump(
        exclude_none=True
    )

    resposta = gerar_resposta(
        pergunta=pergunta,
        intencao=intencao,
        dados=dados,
        filtros_aplicados=filtros_aplicados,
    )

    return {
        "resposta": resposta,
        "intencao": intencao,
        "quantidade_resultados": len(dados),
        "dados": dados,
        "aviso": (
            "Os resultados são baseados em uma amostra de "
            "desenvolvimento com 110 empenhos e não representam "
            "o total de despesas do Estado."
        ),
    }
