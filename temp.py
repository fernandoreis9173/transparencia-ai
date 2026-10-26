from pathlib import Path
import pandas as pd

arquivo = Path(
    "data/processed/empenhos_2025_orgao_48000_funcao_12.parquet"
)

df = pd.read_parquet(arquivo)

empenhos = [
    "2025NE40343",
    "2025NE30224",
    "2025NE38685",
    "2025NE38684",
    "2025NE26885",
    "2025NE38710",
    "2025NE43439",
    "2025NE27025",
    "2025NE24401",
    "2025NE09095",
    "2025NE05096",
]

print("Colunas disponíveis:")
print(df.columns.tolist())

coluna_empenho = "num_empenho"

if coluna_empenho not in df.columns:
    raise ValueError(
        f"Coluna {coluna_empenho!r} não encontrada. "
        "Confira o nome na lista de colunas acima."
    )

resultado = df[
    df[coluna_empenho].astype(str).str.strip().isin(empenhos)
]

print("\nRegistros encontrados:", len(resultado))
print(resultado.to_string(index=False))