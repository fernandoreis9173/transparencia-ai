
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

    # Quando a intenção é consultar anomalias,
    # retorna somente registros sinalizados para verificação.
    if intencao == "anomalias":
        condicoes.append(
            "liquidado_maior_que_empenhado = TRUE"
        )

    # Para outras intenções, aplica o filtro de anomalias
    # somente quando o usuário marcar essa opção.
    elif filtros.apenas_anomalias is True:
        condicoes.append("d.flag_anomalia = %s")
        parametros.append(True)

    where = (
        " WHERE " + " AND ".join(condicoes)
        if condicoes
        else ""
    )

    return where, tuple(parametros)



def contar_empenhos_pendentes(
    filtros: FiltrosChat,
) -> int:
    where, parametros = montar_where(
        filtros,
        "situacao_pagamento",
    )

    condicao_pendente = "situacao_pagamento = %s"

    if where:
        where += f" AND {condicao_pendente}"
    else:
        where = f" WHERE {condicao_pendente}"

    parametros = (*parametros, "NAO_PAGO")

    sql = f"""
        SELECT COUNT(*)
        FROM analytics.vw_despesas_analitica AS d
        {where}
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, parametros)
            resultado = cursor.fetchone()
            return int(resultado[0]) if resultado else 0


def executar_consulta(
    intencao: str,
    filtros: FiltrosChat,
    pergunta: str | None = None,
) -> list[dict]:
    """
    Executa exclusivamente consultas SQL predefinidas.
    Nenhum SQL é gerado pelo modelo de IA.

    Para perguntas de listagem sobre pagamentos, retorna
    os empenhos individualmente. Para perguntas quantitativas,
    mantém o agrupamento por situação.
    """
    where, parametros = montar_where(filtros, intencao)

    texto_pergunta = (pergunta or "").casefold()

    termos_listagem = (
        "quais",
        "liste",
        "listar",
        "mostre os",
        "mostrar os",
        "identifique",
        "detalhe os",
    )

    detalhar_pagamentos = (
        intencao == "situacao_pagamento"
        and any(termo in texto_pergunta for termo in termos_listagem)
    )

    # Consulta específica para listar empenhos pendentes.
    if detalhar_pagamentos:
        sql = """
            SELECT
                num_empenho,
                data_registro_empenho,
                ano_exercicio,
                nome_orgao,
                cod_uo,
                nome_uo,
                nome_favorecido,
                situacao_pagamento,
                vl_empenhado,
                vl_liquidado,
                vl_pago
            FROM analytics.vw_despesas_analitica AS d
        """

        # Se a pergunta for sobre pagamentos pendentes,
        # restringe aos empenhos classificados como não pagos.
        condicao_pendente = "situacao_pagamento = %s"

        if where:
            where += f" AND {condicao_pendente}"
        else:
            where = f" WHERE {condicao_pendente}"

        parametros = (*parametros, "NAO_PAGO")

        sql += where
        sql += """
            ORDER BY vl_empenhado DESC NULLS LAST
            LIMIT 10
        """

    else:
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
                FROM analytics.vw_despesas_analitica AS d
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
                FROM analytics.vw_despesas_analitica AS d
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
                FROM analytics.vw_despesas_analitica AS d
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
                FROM analytics.vw_despesas_analitica AS d
            """,

            "maiores_empenhos": """
                SELECT
                    num_empenho,
                    data_registro_empenho,
                    nome_orgao,
                    nome_uo,
                    nome_favorecido,
                    situacao_pagamento
                    vl_empenhado,
                    vl_liquidado,
                    vl_pago
                FROM analytics.vw_despesas_analitica AS d
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
                FROM analytics.vw_despesas_analitica AS d
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
                FROM analytics.vw_despesas_analitica AS d
            """,
        }

        sql = consultas.get(intencao)

        if sql is None:
            raise HTTPException(
                status_code=400,
                detail="Tipo de consulta não permitido.",
            )

        if intencao == "anomalias":
            # A intenção de anomalias já possui seu próprio filtro.
            pass

        elif intencao == "evolucao_mensal":
            if where:
                where += " AND data_registro_empenho IS NOT NULL"
            else:
                where = " WHERE data_registro_empenho IS NOT NULL"

        sql += where

        if intencao == "top_favorecidos":
            # Ranking padrão: maiores valores empenhados.
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
        pergunta=pergunta,
    )

    filtros_aplicados = payload.filtros.model_dump(
        exclude_none=True
    )

    total_pendentes = None

    if (
        intencao == "situacao_pagamento"
        and any(
            termo in pergunta.casefold()
            for termo in (
                "quais",
                "liste",
                "listar",
                "mostre os",
                "mostrar os",
                "identifique",
                "detalhe os",
            )
        )
    ):
        total_pendentes = contar_empenhos_pendentes(
            payload.filtros
        )

        dados_para_ia = {
            "total_encontrado": total_pendentes,
            "quantidade_exibida": len(dados),
            "empenhos": dados,
        }
    else:
        dados_para_ia = dados

    resultado_ia = gerar_resposta(
        pergunta=pergunta,
        intencao=intencao,
        dados=dados_para_ia,
        filtros_aplicados=filtros_aplicados,
    )

    return {
        "resposta": resultado_ia["resposta"],
        "provedor": resultado_ia["provedor"],
        "intencao": intencao,
        "quantidade_resultados": len(dados),
        "total_pendentes": total_pendentes,
        "dados": dados,
        "aviso": (
            "Os resultados são baseados em uma amostra de "
            "desenvolvimento com 110 empenhos e não representam "
            "o total de despesas do Estado."
        ),
    }
