import requests

url = "https://dadosabertos.sp.gov.br/api/3/action/package_show"

params = {
    "id": "execucao-de-despesas-publicas"
}

response = requests.get(url, params=params)

response.raise_for_status()

data = response.json()

dataset = data["result"]

print("Título:")
print(dataset["title"])

print("\nDescrição:")
print(dataset["notes"])

print("\nRecursos:")

for resource in dataset["resources"]:
    print("\n--------------------------")
    print("Nome:", resource.get("name"))
    print("Formato:", resource.get("format"))
    print("URL:", resource.get("url"))
    print("ID:", resource.get("id"))