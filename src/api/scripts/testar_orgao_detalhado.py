import requests
import pandas as pd

URL = "https://www.transparencia.sp.gov.br/Despesas/Buscar"

payload = {
    "tipoRetorno": "orgao",
    "anoExercicio": 2025,
    "dataInicio": None,
    "dataTermino": None,
    "codigoFiltro": None,
    "nomeFavorecido": None,
    "cpfCnpjFavorecido": None,

    "codOrgao": 48000,

    "codFuncao": None,
    "codSubfuncao": None,
    "codPrograma": None,
    "codAcao": None,
    "codElemento": None,

    "page": 1,
    "pageSize": 50,
    "totalItens": 0
}

print("Consultando órgão 48000...")

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

    print("\n=== PRIMEIROS REGISTROS ===")
    print(df.head(10).to_string(index=False))

    print("\n=== COLUNAS ===")
    print(df.columns.tolist())
else:
    print("Nenhum resultado.")