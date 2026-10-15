import json
import logging

from src.api.services.gemini_service import (
    classificar_pergunta,
    gerar_resposta as gerar_resposta_gemini,
)
from src.api.services.openai_service import gerar_resposta_openai

logger = logging.getLogger(__name__)


def gerar_resposta(
    pergunta: str,
    intencao: str,
    dados: list,
    filtros_aplicados: dict,
) -> str:
    argumentos = {
        "pergunta": pergunta,
        "intencao": intencao,
        "dados": dados,
        "filtros_aplicados": filtros_aplicados,
    }

    try:
        resposta_gemini = gerar_resposta_gemini(**argumentos)

        mensagem = (resposta_gemini or "").strip().lower()

        # O serviço Gemini atual pode retornar uma mensagem de
        # fallback em vez de lançar uma exceção.
        falha_gemini = (
            not mensagem
            or "gemini está temporariamente indisponível" in mensagem
            or "não foi possível gerar uma explicação" in mensagem
            or "não foi possível interpretar a pergunta" in mensagem
        )

        if not falha_gemini:
            logger.info("Resposta gerada pelo Gemini.")
            return {
                "resposta": resposta_gemini,
                "provedor": "gemini",
}

        logger.warning(
            "Gemini indisponível. Tentando OpenAI como alternativa."
        )

    except Exception:
        logger.exception(
            "Falha no Gemini. Tentando OpenAI como alternativa."
        )

    try:
        resposta_openai = gerar_resposta_openai(**argumentos)
        logger.info("Resposta gerada pela OpenAI.")
        return {
            "resposta": resposta_openai,
            "provedor": "openai",
}

    except Exception:
        logger.exception("Gemini e OpenAI não conseguiram responder.")

        return {
            "Não foi possível gerar uma explicação com os provedores de IA. "
            "A consulta ao PostgreSQL foi realizada. "
            "Confira os dados retornados abaixo:\n\n"
            + json.dumps(dados, ensure_ascii=False, indent=2, default=str)
        }


__all__ = ["classificar_pergunta", "gerar_resposta"]
