import requests

url = "https://www.transparencia.sp.gov.br/Home/DespContratosPg"

response = requests.get(url, timeout=30)

print("Status:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))
print("Tamanho:", len(response.text))

print("\nPrimeiros 1000 caracteres:")
print(response.text[:1000])