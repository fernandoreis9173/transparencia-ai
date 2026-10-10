import requests
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

print("Enviando POST...")

response = requests.post(
    URL,
    json=payload,
    timeout=60
)

print("Status:", response.status_code)

print("Content-Type:", response.headers.get("Content-Type"))

print("\nResposta:")

print(response.text[:3000])