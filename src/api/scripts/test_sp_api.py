import requests

url = "https://dadosabertos.sp.gov.br/api/3/action/package_search"

params = {
    "q": "Execução de Despesas Públicas"
}

response = requests.get(url, params=params)

response.raise_for_status()

data = response.json()

print("API funcionando!")
print("Sucesso:", data["success"])
print("Quantidade de resultados:", data["result"]["count"])

for dataset in data["result"]["results"]:
    print("\nDataset:")
    print("Nome:", dataset["name"])
    print("Título:", dataset["title"])