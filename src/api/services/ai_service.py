
import logging
from datetime import date, datetime
from decimal import Decimal

from src.api.services.gemini_service import (
    classificar_pergunta,
    gerar_resposta as gerar_resposta_gemini,
)
from src.api.services.openai_service import gerar_resposta_openai

logger = logging.getLogger(__name__)


AVISO_AMOSTRA = (
    "Os resultados são baseados em uma amostra de desenvolvimento "
    "com 110 empenhos e não representam a totalidade das despesas "
    "do Estado de São Paulo."
)


def formatar_brl(valor) -> str:
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        return "Não informado"

    numero_formatado = f"{numero:,.2f}"
    numero_formatado = (
        numero_formatado
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )
    return f"R$ {numero_formatado}"


def formatar_data(valor) -> str:
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d/%m/%Y")
    return str(valor) if valor else "Não informada"


def formatar_quantidade(valor) -> str:
    try:
        return f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def gerar_fallback_listagem_pagamentos(dados: dict) -> str:
    total = dados.get("total_encontrado", 0)
    empenhos = dados.get("empenhos", [])

    linhas = [
        f"Foram encontrados {formatar_quantidade(total)} "
        "empenhos pendentes de pagamento.",
        "",
        f"Exibindo os {len(empenhos)} registros retornados, "
        "ordenados pelo valor empenhado:",
        "",
    ]

    for item in empenhos:
        linhas.extend([
            f"Empenho: {item.get('num_empenho', 'Não informado')}",
            f"Favorecido: {item.get('nome_favorecido', 'Não informado')}",
            f"Órgão: {item.get('nome_orgao', 'Não informado')}",
            f"Unidade orçamentária: {item.get('nome_uo', 'Não informada')}",
            f"Data do registro: {formatar_data(item.get('data_registro_empenho'))}",
            f"Valor empenhado: {formatar_brl(item.get('vl_empenhado'))}",
            f"Valor liquidado: {formatar_brl(item.get('vl_liquidado'))}",
            f"Valor pago: {formatar_brl(item.get('vl_pago'))}",
            "",
        ])

    if total > len(empenhos):
        linhas.append(
            f"Observação: foram encontrados {formatar_quantidade(total)} "
            f"registros, mas apenas {len(empenhos)} são exibidos nesta resposta."
        )

    linhas.extend(["", AVISO_AMOSTRA])
    return "\n".join(linhas)


def gerar_fallback_resumo(dados) -> str:
    registro = dados[0] if isinstance(dados, list) and dados else dados

    if not isinstance(registro, dict):
        return "A consulta foi realizada, mas não retornou um resumo disponível."

    linhas = [
        "Resumo da execução das despesas públicas:",
        "",
        f"Quantidade de empenhos: "
        f"{formatar_quantidade(registro.get('quantidade_empenhos'))}",
        f"Total empenhado: {formatar_brl(registro.get('total_empenhado'))}",
        f"Total liquidado: {formatar_brl(registro.get('total_liquidado'))}",
        f"Total pago: {formatar_brl(registro.get('total_pago'))}",
        "",
        "Situação dos pagamentos:",
        f"- Não pagos: {formatar_quantidade(registro.get('quantidade_nao_pago'))}",
        f"- Pagamento parcial: "
        f"{formatar_quantidade(registro.get('quantidade_pagamento_parcial'))}",
        f"- Pagos: {formatar_quantidade(registro.get('quantidade_pago'))}",
        "",
        f"Registros sinalizados para análise: "
        f"{formatar_quantidade(registro.get('quantidade_anomalias'))}",
        "",
        AVISO_AMOSTRA,
    ]
    return "\n".join(linhas)


def gerar_fallback_situacao_pagamento(dados) -> str:
    if not isinstance(dados, list) or not dados:
        return "Não foram encontrados registros para os filtros informados."

    nomes = {
        "NAO_PAGO": "Não pago",
        "PAGAMENTO_PARCIAL": "Pagamento parcial",
        "PAGO": "Pago",
    }

    linhas = ["Resumo da situação dos pagamentos:", ""]

    for item in dados:
        situacao = nomes.get(
            item.get("situacao_pagamento"),
            item.get("situacao_pagamento", "Não informada"),
        )
        linhas.extend([
            f"Situação: {situacao}",
            f"Quantidade de empenhos: "
            f"{formatar_quantidade(item.get('quantidade_empenhos'))}",
            f"Total empenhado: {formatar_brl(item.get('total_empenhado'))}",
            f"Total liquidado: {formatar_brl(item.get('total_liquidado'))}",
            f"Total pago: {formatar_brl(item.get('total_pago'))}",
            "",
        ])

    linhas.append(AVISO_AMOSTRA)
    return "\n".join(linhas)


def gerar_fallback_listagem(dados, intencao: str) -> str:
    if not isinstance(dados, list) or not dados:
        return "Não foram encontrados registros para os filtros informados."

    linhas = []

    if intencao == "anomalias":
        linhas.extend([
            "Registros sinalizados para análise:",
            "",
            "O critério utilizado identifica casos em que o valor "
            "liquidado supera o valor empenhado. Isso é um alerta "
            "para verificação, não uma comprovação de irregularidade.",
            "",
        ])
    elif intencao == "maiores_empenhos":
        linhas.extend([
            "Maiores empenhos por valor empenhado:",
            "",
        ])
    elif intencao == "top_favorecidos":
        linhas.extend([
            "Favorecidos com maiores valores empenhados:",
            "",
        ])
    elif intencao == "unidades":
        linhas.extend([
            "Resumo por unidade orçamentária:",
            "",
        ])
    elif intencao == "evolucao_mensal":
        linhas.extend([
            "Evolução mensal das despesas:",
            "",
        ])

    for indice, item in enumerate(dados, start=1):
        if intencao == "anomalias":
            diferenca = item.get("diferenca_liquidado_empenhado")
            linhas.extend([
                f"{indice}. Empenho: {item.get('num_empenho', 'Não informado')}",
                f"   Favorecido: {item.get('nome_favorecido', 'Não informado')}",
                f"   Órgão: {item.get('nome_orgao', 'Não informado')}",
                f"   Valor empenhado: {formatar_brl(item.get('vl_empenhado'))}",
                f"   Valor liquidado: {formatar_brl(item.get('vl_liquidado'))}",
                f"   Diferença liquidado - empenhado: {formatar_brl(diferenca)}",
                "",
            ])

        elif intencao == "maiores_empenhos":
            linhas.extend([
                f"{indice}. Empenho: {item.get('num_empenho', 'Não informado')}",
                f"   Favorecido: {item.get('nome_favorecido', 'Não informado')}",
                f"   Unidade: {item.get('nome_uo', 'Não informada')}",
                f"   Data: {formatar_data(item.get('data_registro_empenho'))}",
                f"   Valor empenhado: {formatar_brl(item.get('vl_empenhado'))}",
                f"   Valor liquidado: {formatar_brl(item.get('vl_liquidado'))}",
                f"   Valor pago: {formatar_brl(item.get('vl_pago'))}",
                "",
            ])

        elif intencao == "top_favorecidos":
            linhas.extend([
                f"{indice}. {item.get('nome_favorecido', 'Não informado')}",
                f"   Quantidade de empenhos: "
                f"{formatar_quantidade(item.get('quantidade_empenhos'))}",
                f"   Total empenhado: {formatar_brl(item.get('total_empenhado'))}",
                f"   Total pago: {formatar_brl(item.get('total_pago'))}",
                "",
            ])

        elif intencao == "unidades":
            linhas.extend([
                f"{indice}. {item.get('nome_uo', 'Não informada')}",
                f"   Código: {item.get('cod_uo', 'Não informado')}",
                f"   Quantidade de empenhos: "
                f"{formatar_quantidade(item.get('quantidade_empenhos'))}",
                f"   Total empenhado: {formatar_brl(item.get('total_empenhado'))}",
                "",
            ])

        elif intencao == "evolucao_mensal":
            linhas.extend([
                f"{indice}. Mês: {formatar_data(item.get('mes'))}",
                f"   Quantidade de empenhos: "
                f"{formatar_quantidade(item.get('quantidade_empenhos'))}",
                f"   Total empenhado: {formatar_brl(item.get('total_empenhado'))}",
                f"   Total liquidado: {formatar_brl(item.get('total_liquidado'))}",
                f"   Total pago: {formatar_brl(item.get('total_pago'))}",
                "",
            ])

    linhas.extend(["", AVISO_AMOSTRA])
    return "\n".join(linhas)


def gerar_fallback(dados, intencao: str) -> str:
    if (
        intencao == "situacao_pagamento"
        and isinstance(dados, dict)
        and "total_encontrado" in dados
        and "empenhos" in dados
    ):
        return gerar_fallback_listagem_pagamentos(dados)

    if intencao == "resumo":
        return gerar_fallback_resumo(dados)

    if intencao == "situacao_pagamento":
        return gerar_fallback_situacao_pagamento(dados)

    if intencao in {
        "anomalias",
        "maiores_empenhos",
        "top_favorecidos",
        "unidades",
        "evolucao_mensal",
    }:
        return gerar_fallback_listagem(dados, intencao)

    return (
        "A consulta ao PostgreSQL foi realizada, mas ainda não existe "
        "um formatador específico para essa intenção."
    )


def resposta_indisponivel(resposta: str | None) -> bool:
    mensagem = (resposta or "").strip().casefold()

    return (
        not mensagem
        or "gemini está temporariamente indisponível" in mensagem
        or "não foi possível gerar uma explicação" in mensagem
        or "não foi possível interpretar a pergunta" in mensagem
        or "não foi possível gerar uma resposta" in mensagem
    )


def gerar_resposta(
    pergunta: str,
    intencao: str,
    dados: list | dict,
    filtros_aplicados: dict,
) -> dict:
    argumentos = {
        "pergunta": pergunta,
        "intencao": intencao,
        "dados": dados,
        "filtros_aplicados": filtros_aplicados,
    }

    try:
        resposta = gerar_resposta_gemini(**argumentos)

        if not resposta_indisponivel(resposta):
            logger.info("Resposta gerada pelo Gemini.")
            return {"resposta": resposta.strip(), "provedor": "gemini"}

        logger.warning("Gemini indisponível. Tentando OpenAI.")

    except Exception:
        logger.exception("Falha no Gemini. Tentando OpenAI.")

    try:
        resposta = gerar_resposta_openai(**argumentos)

        if not resposta_indisponivel(resposta):
            logger.info("Resposta gerada pela OpenAI.")
            return {"resposta": resposta.strip(), "provedor": "openai"}

        logger.warning("OpenAI retornou uma mensagem de indisponibilidade.")

    except Exception:
        logger.exception("Falha na OpenAI.")

    logger.warning("Usando resposta formatada localmente.")
    return {
        "resposta": gerar_fallback(dados, intencao),
        "provedor": "postgresql_fallback",
    }


__all__ = ["classificar_pergunta", "gerar_resposta"]
