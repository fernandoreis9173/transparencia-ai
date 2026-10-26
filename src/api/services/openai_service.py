import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def gerar_resposta_openai(
    pergunta: str,
    intencao: str,
    dados: list | dict,
    filtros_aplicados: dict,
) -> str:
    if not API_KEY:
        raise RuntimeError("OPENAI_API_KEY não configurada.")

    cliente = OpenAI(api_key=API_KEY)

    contexto = {
        "pergunta": pergunta,
        "intencao": intencao,
        "filtros_aplicados": filtros_aplicados,
        "dados_postgresql": dados,
    }

    instrucoes = f"""
Você é um assistente de análise de despesas públicas.

Responda em português brasileiro, com clareza e objetividade.
Utilize exclusivamente os dados fornecidos no contexto.
Não invente valores, órgãos, datas ou conclusões.
Diferencie quantidade de registros de valores monetários.
Se os dados não forem suficientes, informe essa limitação.
Não afirme que uma anomalia comprova fraude ou irregularidade.
Informe valores monetários em reais quando apropriado.

Os dados pertencem a uma amostra de desenvolvimento com
110 empenhos e não representam o total de despesas do Estado.

Contexto:
{json.dumps(contexto, ensure_ascii=False, default=str)}
"""

    resposta = cliente.responses.create(
        model=MODEL,
        input=instrucoes,
    )

    texto = (resposta.output_text or "").strip()

    if not texto:
        raise RuntimeError("A OpenAI retornou uma resposta vazia.")

    return texto
