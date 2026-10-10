import requests

base_url = "https://www.transparencia.sp.gov.br"

url = f"{base_url}/Despesas"

response = requests.get(url, timeout=30)

print("Status:", response.status_code)
print("URL final:", response.url)
print("Content-Type:", response.headers.get("Content-Type"))
print("Tamanho:", len(response.text))

print("\n=== TÍTULO ===")

from bs4 import BeautifulSoup

soup = BeautifulSoup(response.text, "html.parser")

print(soup.title.text.strip() if soup.title else "Sem título")

print("\n=== FORMULÁRIOS ===")

for form in soup.find_all("form"):
    print("Action:", form.get("action"))
    print("Method:", form.get("method"))

print("\n=== SCRIPTS ===")

for script in soup.find_all("script"):
    src = script.get("src")

    if src:
        print(src)

print("\n=== AJAX / ENDPOINTS NO HTML ===")

html = response.text

for palavra in ["ajax", "$.ajax", "fetch", "/Despesas", "json", "url:"]:
    print(f"{palavra}: {html.lower().count(palavra.lower())}")