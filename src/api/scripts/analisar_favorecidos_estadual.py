import pandas as pd
import re

ARQUIVO = "data/raw/favorecidos_2025_estadual.csv"

df = pd.read_csv(
    ARQUIVO,
    dtype={"cnpj_cpf_favorecido": str},
    encoding="utf-8-sig"
)

# Normalizar documentos
df["documento"] = (
    df["cnpj_cpf_favorecido"]
    .fillna("")
    .str.strip()
)

# Identificar CPF/CNPJ numéricos válidos em formato
df["documento_numerico"] = df["documento"].str.fullmatch(
    r"\d{11}|\d{14}"
)

validos = df[df["documento_numerico"]].copy()
invalidos = df[~df["documento_numerico"]].copy()

print("\n========== RESUMO ==========")
print(f"Total de registros: {len(df)}")
print(f"Documentos numéricos (11 ou 14 dígitos): {len(validos)}")
print(f"Identificadores especiais/outros: {len(invalidos)}")
print(f"Documentos numéricos distintos: {validos['documento'].nunique()}")
print(f"Documentos repetidos: {validos['documento'].duplicated().sum()}")

print("\n========== 20 MAIORES FAVORECIDOS NUMÉRICOS ==========")

colunas = [
    "cnpj_cpf_favorecido",
    "nome_favorecido",
    "vl_empenhado"
]

print(
    validos[colunas]
    .sort_values("vl_empenhado", ascending=False)
    .head(20)
    .to_string(index=False)
)

print("\n========== 20 MAIORES IDENTIFICADORES ESPECIAIS ==========")

print(
    invalidos[colunas]
    .sort_values("vl_empenhado", ascending=False)
    .head(20)
    .to_string(index=False)
)