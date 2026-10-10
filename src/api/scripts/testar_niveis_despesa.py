import requests
import pandas as pd

URL = "https://www.transparencia.sp.gov.br/Despesas/Buscar"

TIPOS = [
    "orgao",
    "funcao",
    "programa",
    "favorecido"
]


def consultar(tipo):
    payload = {
        "tipoRetorno": tipo,
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

    print(f"\n{'=' * 60}")
    print(f"CONSULTANDO: {tipo.upper()}")
    print(f"{'=' * 60}")

    response = requests.post(
        URL,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    dados = response.json()

    print("Status:", response.status_code)
    print("Etapa:", dados.get("etapaAtual"))
    print("Página:", dados.get("page"))
    print("Total de páginas:", dados.get("totalPages"))
    print("Total de itens:", dados.get("totalItems"))
    print("Page size:", dados.get("pageSize"))

    items = dados.get("items", [])

    print("Registros recebidos:", len(items))

    if items:
        df = pd.DataFrame(items)

        print("\nColunas:")
        print(df.columns.tolist())

        print("\nPrimeiros registros:")
        print(df.head(5).to_string())

    return dados


for tipo in TIPOS:
    try:
        consultar(tipo)
    except Exception as e:
        print(f"ERRO em {tipo}:")
        print(e)