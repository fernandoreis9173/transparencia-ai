import pandas as pd

from src.api.scripts.despesas_extractor import DespesasExtractor

ARQUIVO = "data/raw/favorecidos_2025_estadual.csv"

df = pd.read_csv(
    ARQUIVO,
    dtype={"cnpj_cpf_favorecido": str},
    encoding="utf-8-sig"
)

# Selecionar o maior favorecido com documento numérico
df["documento"] = (
    df["cnpj_cpf_favorecido"]
    .fillna("")
    .str.strip()
)

validos = df[
    df["documento"].str.fullmatch(r"\d{11}|\d{14}", na=False)
].copy()

validos["vl_empenhado"] = pd.to_numeric(
    validos["vl_empenhado"],
    errors="coerce"
)

favorecido = validos.sort_values(
    "vl_empenhado",
    ascending=False
).iloc[0]

documento = favorecido["documento"]

print("Favorecido selecionado:")
print(f"Documento: {documento}")
print(f"Nome: {favorecido['nome_favorecido']}")
print(f"Total agregado empenhado: {favorecido['vl_empenhado']}")

documento = "22770554000100"

favorecido = df[
    df["documento"] == documento
].iloc[0]

print("Favorecido selecionado:")
print(f"Documento: {documento}")
print(f"Nome: {favorecido['nome_favorecido']}")
print(f"Total agregado empenhado: {favorecido['vl_empenhado']}")

extractor = DespesasExtractor()

df_empenhos = extractor.buscar_empenhos(
    ano=2025,
    cpf_cnpj=documento,
    page_size=20,
    cod_orgao=None,
    cod_funcao=None,
)

print("\n========== RESULTADO DETALHADO ==========")
print(f"Linhas recebidas: {len(df_empenhos)}")
print(
    "Empenhos distintos:",
    df_empenhos["num_empenho"].nunique()
)

print("\nEmpenhos repetidos:")
print(
    df_empenhos[
        df_empenhos.duplicated(
            subset=["num_empenho"],
            keep=False
        )
    ][
        ["num_empenho", "cod_orgao", "cod_uo"]
    ].sort_values("num_empenho").to_string(index=False)
)

for coluna in ["vl_empenhado", "vl_liquidado", "vl_pago"]:
    total = pd.to_numeric(
        df_empenhos[coluna],
        errors="coerce"
    ).sum()

    agregado = pd.to_numeric(
        pd.Series([favorecido[coluna]]),
        errors="coerce"
    ).iloc[0]

    print(f"\n{coluna}:")
    print(f"Agregado: {agregado:.2f}")
    print(f"Detalhado: {total:.2f}")
    print(f"Diferença: {total - agregado:.2f}")