import requests
import re

url = "https://www.transparencia.sp.gov.br/Despesas"

response = requests.get(url, timeout=30)
response.raise_for_status()

html = response.text

print("Página carregada:", len(html), "caracteres")

print("\n" + "=" * 60)
print("TRECHOS COM $.ajax")
print("=" * 60)

for match in re.finditer(r"\$\.ajax", html, re.IGNORECASE):
    inicio = max(0, match.start() - 1000)
    fim = min(len(html), match.end() + 3000)

    print(html[inicio:fim])
    print("\n" + "-" * 60)


print("\n" + "=" * 60)
print("TRECHOS COM fetch")
print("=" * 60)

for match in re.finditer(r"\bfetch\s*\(", html, re.IGNORECASE):
    inicio = max(0, match.start() - 1000)
    fim = min(len(html), match.end() + 3000)

    print(html[inicio:fim])
    print("\n" + "-" * 60)