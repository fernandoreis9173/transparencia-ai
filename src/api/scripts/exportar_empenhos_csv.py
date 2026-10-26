
from pathlib import Path
import pandas as pd

# O script está em src/api/scripts; sobe três níveis até a raiz
raiz = Path(__file__).resolve().parents[3]

origem = (
    raiz / "data" / "processed"
    / "empenhos_2025_orgao_48000_funcao_12.parquet"
)

destino = (
    raiz / "data" / "processed"
    / "empenhos_2025_orgao_48000_funcao_12.csv"
)

print(f"Raiz do projeto: {raiz}")
print(f"Arquivo de origem: {origem}")

if not origem.exists():
    raise FileNotFoundError(
        f"Parquet não encontrado: {origem}"
    )

df = pd.read_parquet(origem)

# Identificador da fonte confirmada em core.fonte
df["fonte_id"] = 1

print(f"Registros encontrados: {len(df)}")
print(f"Quantidade de colunas: {len(df.columns)}")

if "num_empenho" not in df.columns:
    raise ValueError(
        "A coluna num_empenho não existe no arquivo."
    )

print(
    "Empenhos sem número:",
    df["num_empenho"].isna().sum()
)

df.to_csv(
    destino,
    index=False,
    encoding="utf-8",
    na_rep=""
)

print(f"CSV gerado com sucesso: {destino}")
