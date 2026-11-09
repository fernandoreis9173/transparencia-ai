
from src.api.scripts.despesas_extractor import DespesasExtractor
from src.api.scripts.extrair_empenhos_2025 import ANO
import pandas as pd

PAGE_SIZE = 500

extractor = DespesasExtractor(
    timeout=60,
    max_retries=3,
    delay=0.2,
)

df = extractor.buscar_favorecidos(
    ano=ANO,
    page_size=PAGE_SIZE,
    cod_orgao=None,
    cod_funcao=None,
)

# Salvar todos os favorecidos extraídos
caminho = "data/raw/favorecidos_2025_estadual.csv"

extractor.salvar_csv(df, caminho)

print(f"Arquivo salvo: {caminho}")
print(f"Total de favorecidos: {len(df)}")

# Demais comandos de exibição...
print(df.head())

if "num_empenho" in df.columns:
    print("A consulta agregada contém num_empenho.")
    print(df.head())
else:
    print("A consulta agregada não contém num_empenho.")

print(f"Favorecidos encontrados: {len(df)}")

# Exibe os maiores favorecidos por valor empenhado.
df["vl_empenhado"] = (
    df["vl_empenhado"]
    .astype(str)
    .str.replace(",", ".", regex=False)
)

df["vl_empenhado"] = pd.to_numeric(
    df["vl_empenhado"],
    errors="coerce",
)

print(
    df.nlargest(10, "vl_empenhado")[
        ["cnpj_cpf_favorecido", "nome_favorecido", "vl_empenhado"]
    ].to_string(index=False)
)
