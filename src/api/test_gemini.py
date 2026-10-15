
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise SystemExit(
        "ERRO: GEMINI_API_KEY não encontrada no arquivo .env."
    )

client = genai.Client(api_key=api_key)

print("\n1. Consultando modelos disponíveis...")

try:
    modelos_disponiveis = {}

    for modelo in client.models.list():
        nome = (getattr(modelo, "name", "") or "").replace(
            "models/", ""
        )
        acoes = getattr(modelo, "supported_actions", None) or []

        if "generateContent" in acoes:
            modelos_disponiveis[nome] = True

    candidatos = [
        "gemini-3.8-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
    ]

    print("\nModelos candidatos encontrados:")
    for nome in candidatos:
        status = (
            "DISPONÍVEL NA LISTA"
            if nome in modelos_disponiveis
            else "NÃO ENCONTRADO NA LISTA"
        )
        print(f"- {nome}: {status}")

except Exception as erro:
    raise SystemExit(
        "Não foi possível consultar os modelos. "
        f"Verifique a chave, a conexão e as permissões. Erro: {erro}"
    )


print("\n2. Testando geração de texto...")

for nome in candidatos:
    if nome not in modelos_disponiveis:
        continue

    print(f"\nTestando {nome}...")

    try:
        resposta = client.models.generate_content(
            model=nome,
            contents=(
                "Responda em português brasileiro, em uma frase: "
                "o que significa valor empenhado em despesas públicas?"
            ),
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=150,
            ),
        )

        texto = (resposta.text or "").strip()

        if texto:
            print(f"\nSUCESSO: {nome}")
            print(f"Resposta: {texto}")
            print(
                f"\nConfigure GEMINI_MODEL={nome} no arquivo .env."
            )
            break

        print("O modelo não retornou texto.")

    except Exception as erro:
        print(f"Falha em {nome}: {erro}")

else:
    print(
        "\nNenhum modelo candidato conseguiu gerar texto. "
        "Confira o erro retornado para identificar se é "
        "sobrecarga, cota, chave ou permissão."
    )
