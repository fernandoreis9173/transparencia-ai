import requests
import pandas as pd
import json

URL = "https://www.transparencia.sp.gov.br/Despesas/Buscar"

payload = {
    "tipoRetorno": "orgao",
    "anoExercicio": 2025,
    "dataInicio": None,
    "dataTermino": None,
    "codigoFiltro": None,
    "nomeFavorecido": None,
    "cpfCnpjFavorecido": None,
    "codOrgao": None,
    "codFuncao": None,
    "codSubfuncao": None,
    "codPrograma": None,
    "codAcao": None,
    "codElemento": None,
    "page": 1,
    "pageSize": 50,
    "totalItens": 0
}

print("Consultando Portal da Transparência...")

response = requests.post(
    URL,
    json=payload,
    timeout=60
)

print("Status:", response.status_code)

response.raise_for_status()

dados = response.json()

print("\n=== RESPOSTA ===")
print(json.dumps(dados, indent=2, ensure_ascii=False)[:10000])

print("\n=== INFORMAÇÕES ===")

print("Página:", dados.get("page"))
print("Total de páginas:", dados.get("totalPages"))
print("Total de itens:", dados.get("totalItems"))
print("Tamanho da página:", dados.get("pageSize"))
print("Etapa atual:", dados.get("etapaAtual"))
print("Última atualização:", dados.get("ultimaAtualizacao"))

items = dados.get("items", [])

print("\nQuantidade de registros recebidos:", len(items))

if items:
    df = pd.DataFrame(items)

    print("\n=== COLUNAS ===")
    print(df.columns.tolist())

    print("\n=== TODOS OS 28 REGISTROS ===")
    print(df.to_string(index=False))

    print("\n=== TIPOS DAS COLUNAS ===")
    print(df.dtypes)

    df.to_csv(
        "data/raw/despesas_2025_pagina_1.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\nArquivo salvo:")
    print("data/raw/despesas_2025_pagina_1.csv")

else:
    print("\nNenhum registro retornado.")