import requests
import pandas as pd
import time

URL = "https://www.transparencia.sp.gov.br/Despesas/Buscar"

# Vamos pegar mais favorecidos da primeira página
payload_favorecidos = {
    "tipoRetorno": "orgao",
    "anoExercicio": 2025,
    "dataInicio": None,
    "dataTermino": None,
    "codigoFiltro": None,
    "nomeFavorecido": None,
    "cpfCnpjFavorecido": None,

    "codOrgao": 48000,
    "codFuncao": 12,
    "codSubfuncao": None,
    "codPrograma": None,
    "codAcao": None,
    "codElemento": None,

    "page": 1,
    "pageSize": 50,
    "totalItens": 0
}

response = requests.post(
    URL,
    json=payload_favorecidos,
    timeout=60
)

data = response.json()

items = data.get("items", [])

df = pd.DataFrame(items)

print(f"Favorecidos encontrados: {len(df)}")

resultados = []

for _, row in df.iterrows():

    cpf_cnpj = row["cnpj_cpf_favorecido"]
    nome = row["nome_favorecido"]

    payload_empenhos = {
        "tipoRetorno": "favorecido",
        "anoExercicio": 2025,
        "dataInicio": None,
        "dataTermino": None,
        "codigoFiltro": None,

        "nomeFavorecido": None,
        "cpfCnpjFavorecido": str(cpf_cnpj),

        "codOrgao": 48000,
        "codFuncao": 12,
        "codSubfuncao": None,
        "codPrograma": None,
        "codAcao": None,
        "codElemento": None,

        "page": 1,
        "pageSize": 1,
        "totalItens": 0
    }

    try:

        response = requests.post(
            URL,
            json=payload_empenhos,
            timeout=60
        )

        data_empenhos = response.json()

        total = data_empenhos.get("totalItems", 0)

        resultados.append({
            "cpf_cnpj": cpf_cnpj,
            "nome": nome,
            "total_empenhos": total
        })

        print(
            f"{cpf_cnpj} | "
            f"{str(nome)[:45]:45} | "
            f"{total} empenhos"
        )

        time.sleep(0.2)

    except Exception as e:

        print(
            f"Erro ao consultar {cpf_cnpj}: {e}"
        )


resultado_df = pd.DataFrame(resultados)

print("\n" + "=" * 80)

print("\nTOP FAVORECIDOS POR QUANTIDADE DE EMPENHOS")

print(
    resultado_df
    .sort_values("total_empenhos", ascending=False)
    .head(20)
    .to_string(index=False)
)