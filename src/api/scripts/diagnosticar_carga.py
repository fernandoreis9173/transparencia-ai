
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
PASTA = RAIZ / "data" / "raw" / "empenhos"

arquivos = list(PASTA.glob("*.csv"))
frames = []

for arquivo in arquivos:
    try:
        df = pd.read_csv(
            arquivo,
            dtype=str,
            encoding="utf-8-sig",
        )

        if "num_empenho" not in df.columns:
            print(f"Sem num_empenho: {arquivo.name}")
            continue

        df["arquivo_origem"] = arquivo.name
        frames.append(df)

    except Exception as erro:
        print(f"Erro em {arquivo.name}: {erro}")

if not frames:
    raise SystemExit("Nenhum CSV válido encontrado.")

dados = pd.concat(frames, ignore_index=True)

dados["num_empenho"] = (
    dados["num_empenho"].astype("string").str.strip()
)

validos = dados[
    dados["num_empenho"].notna()
    & dados["num_empenho"].ne("")
]

print("\n--- DIAGNÓSTICO DOS CSVs BRUTOS ---")
print(f"Arquivos encontrados: {len(arquivos)}")
print(f"Arquivos lidos: {len(frames)}")
print(f"Linhas lidas: {len(dados)}")
print(f"Linhas com número de empenho: {len(validos)}")
print(
    "Empenhos únicos: "
    f"{validos['num_empenho'].nunique()}"
)
print(
    "Números de empenho repetidos: "
    f"{validos['num_empenho'].duplicated().sum()}"
)

print("\n--- EXEMPLOS DE DUPLICIDADE ---")
duplicados = validos[
    validos["num_empenho"].duplicated(keep=False)
]

if duplicados.empty:
    print("Nenhum empenho repetido.")
else:
    colunas = [
        c for c in [
            "num_empenho",
            "nome_favorecido",
            "vl_empenhado",
            "vl_liquidado",
            "arquivo_origem",
        ]
        if c in duplicados.columns
    ]
    print(
        duplicados[colunas]
        .sort_values("num_empenho")
        .head(30)
        .to_string(index=False)
    )
