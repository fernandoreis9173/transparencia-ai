import requests
import re

url = "https://www.transparencia.sp.gov.br/Despesas"

response = requests.get(url, timeout=30)
response.raise_for_status()

html = response.text

padrao = r'function\s+montarFiltro\s*\([^)]*\)\s*\{'

match = re.search(padrao, html, re.IGNORECASE)

if not match:
    print("Função montarFiltro não encontrada.")
    exit()

inicio = match.start()

# Mostra aproximadamente 8.000 caracteres a partir da função
trecho = html[inicio:inicio + 8000]

print("=" * 70)
print("FUNÇÃO montarFiltro()")
print("=" * 70)
print(trecho)