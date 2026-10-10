import requests
import pandas as pd

URL = "https://www.transparencia.sp.gov.br/Despesas/Buscar"

CPF_CNPJ = "32691514000127"

def consultar_pagina(page):

    payload = {
        "tipoRetorno": "favorecido",
        "anoExercicio": 2025,
        "dataInicio": None,
        "dataTermino": None,
        "codigoFiltro": None,

        "nomeFavorecido": None,
        "cpfCnpjFavorecido": CPF_CNPJ,

        "codOrgao": 48000,
        "codFuncao": 12,
        "codSubfuncao": None,
        "codPrograma": None,
        "codAcao": None,
        "codElemento": None,

        "page": page,
        "pageSize": 5,
        "totalItens": 0
    }

    response = requests.post(
        URL,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    return response.json()


print("Consultando favorecido:")
print(CPF_CNPJ)
print("2M-COMERCIO DE ELETROELETRONICOS LTDA")

# Primeira consulta para descobrir quantidade total
data = consultar_pagina(1)

print("\n=== RESUMO ===")
print("Status: 200")
print("Etapa:", data.get("etapaAtual"))
print("Total de itens:", data.get("totalItems"))
print("Total de páginas:", data.get("totalPages"))
print("Page size:", data.get("pageSize"))

total_paginas = data.get("totalPages", 0)

todos_empenhos = []

for page in range(1, total_paginas + 1):

    print(f"\n--- PÁGINA {page}/{total_paginas} ---")

    data = consultar_pagina(page)

    items = data.get("items", [])

    print("Registros:", len(items))

    for item in items:
        todos_empenhos.append(item)

    if items:
        df = pd.DataFrame(items)

        colunas = [
            "num_empenho",
            "data_registro_empenho",
            "vl_empenhado",
            "vl_liquidado",
            "vl_pago",
            "cod_subfuncao",
            "cod_programa",
            "cod_acao"
        ]

        colunas_existentes = [
            c for c in colunas
            if c in df.columns
        ]

        print(
            df[colunas_existentes]
            .to_string(index=False)
        )


print("\n" + "=" * 80)

print("TOTAL COLETADO:", len(todos_empenhos))

df_final = pd.DataFrame(todos_empenhos)

if not df_final.empty:

    print("\n=== EMPENHOS ÚNICOS ===")

    print(
        df_final["num_empenho"]
        .nunique()
    )

    print("\n=== NÚMEROS DOS EMPENHOS ===")

    print(
        df_final["num_empenho"]
        .tolist()
    )