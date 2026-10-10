import requests
import re

url = "https://www.transparencia.sp.gov.br/Despesas"

response = requests.get(url, timeout=30)
response.raise_for_status()

html = response.text

padrao = r'function\s+montarFiltroBase\s*\([^)]*\)\s*\{'

match = re.search(padrao, html, re.IGNORECASE)

if not match:
    print("Função montarFiltroBase não encontrada.")
    exit()

inicio = match.start()

trecho = html[inicio:inicio + 12000]

print("=" * 70)
print("FUNÇÃO montarFiltroBase()")
print("=" * 70)
print(trecho)