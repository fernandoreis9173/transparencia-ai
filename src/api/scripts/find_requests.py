import requests
import re

url = "https://www.transparencia.sp.gov.br/Home/DespContratosPg"

response = requests.get(url, timeout=30)
response.raise_for_status()

html = response.text

print("=== POSSÍVEIS ENDPOINTS ===")

patterns = [
    r'url\s*:\s*["\']([^"\']+)',
    r'ajax\s*\(\s*["\']([^"\']+)',
    r'fetch\s*\(\s*["\']([^"\']+)',
    r'ajax\s*\(\s*\{[^}]*url\s*:\s*["\']([^"\']+)',
    r'action\s*=\s*["\']([^"\']+)',
    r'href\s*=\s*["\']([^"\']+)'
]

encontrados = set()

for pattern in patterns:
    resultados = re.findall(
        pattern,
        html,
        re.IGNORECASE | re.DOTALL
    )

    for resultado in resultados:
        if resultado not in encontrados:
            encontrados.add(resultado)
            print(resultado)

print("\n=== PALAVRAS RELACIONADAS A API/DADOS ===")

palavras = [
    "api",
    "ajax",
    "json",
    "despesa",
    "pagamento",
    "empenho",
    "liquidacao",
    "dotacao",
    "consulta"
]

for palavra in palavras:
    quantidade = html.lower().count(palavra.lower())
    print(f"{palavra}: {quantidade}")