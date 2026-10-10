import requests
import pandas as pd

URL = "https://www.transparencia.sp.gov.br/Despesas/Buscar"

payload = {
    "tipoRetorno": "favorecido",
    "anoExercicio": 2025,
    "dataInicio": None,
    "dataTermino": None,
    "codigoFiltro": None,

    # IMPORTANTE:
    # nenhum favorecido específico
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

print("Consultando favorecidos sem CPF/CNPJ específico...")

response = requests.post(
    URL,
    json=payload,
    timeout=60
)

print("\n=== INFORMAÇÕES ===")
print("Status:", response.status_code)

data = response.json()

print("Etapa:", data.get("etapaAtual"))
print("Página:", data.get("page"))
print("Total de páginas:", data.get("totalPages"))
print("Total de itens:", data.get("totalItems"))
print("Page size:", data.get("pageSize"))

items = data.get("items", [])

print("\nQuantidade de registros:", len(items))

if items:
    df = pd.DataFrame(items)

    print("\n=== PRIMEIROS REGISTROS ===")
    print(df.head(10).to_string(index=False))

    print("\n=== COLUNAS ===")
    print(df.columns.tolist())