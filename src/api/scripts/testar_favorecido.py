import requests
import pandas as pd

URL = "https://www.transparencia.sp.gov.br/Despesas/Buscar"

payload = {
    "tipoRetorno": "favorecido",
    "anoExercicio": 2025,
    "dataInicio": None,
    "dataTermino": None,
    "codigoFiltro": None,
    "nomeFavorecido": None,
    "cpfCnpjFavorecido": "06993919621",
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

print("Consultando favorecido...")

response = requests.post(
    URL,
    json=payload,
    timeout=60
)

response.raise_for_status()

dados = response.json()

print("\n=== INFORMAÇÕES ===")
print("Status:", response.status_code)
print("Etapa:", dados.get("etapaAtual"))
print("Página:", dados.get("page"))
print("Total de páginas:", dados.get("totalPages"))
print("Total de itens:", dados.get("totalItems"))
print("Page size:", dados.get("pageSize"))

items = dados.get("items", [])

print("\nQuantidade de registros:", len(items))

if items:
    df = pd.DataFrame(items)

    print("\n=== COLUNAS ===")
    print(df.columns.tolist())

    print("\n=== RESULTADOS ===")
    print(df.to_string(index=False))
else:
    print("\nNenhum resultado encontrado.")