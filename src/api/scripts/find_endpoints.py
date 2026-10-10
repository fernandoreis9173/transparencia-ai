import requests
import re

url = "https://www.transparencia.sp.gov.br/Home/DespContratosPg"

response = requests.get(url, timeout=30)
response.raise_for_status()

html = response.text

print("Página carregada com sucesso!")
print("Tamanho:", len(html))

print("\n=== URLs encontradas ===")

urls = re.findall(r'https?://[^"\']+', html)

for url in urls:
    print(url)

print("\n=== Arquivos JavaScript ===")

scripts = re.findall(
    r'<script[^>]+src=["\']([^"\']+)["\']',
    html,
    re.IGNORECASE
)

for script in scripts:
    print(script)