
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
PASTA_RAW = RAIZ / "data" / "raw" / "empenhos"
PASTA_PROCESSED = RAIZ / "data" / "processed"

ARQUIVO_ATUAL = (
    PASTA_PROCESSED
    / "empenhos_2025_orgao_48000_funcao_12.csv"
)
ARQUIVO_SAIDA = (
    PASTA_PROCESSED
    / "empenhos_pendentes.csv"
)

CHAVE = "num_empenho"


def ler_csv(caminho: Path) -> pd.DataFrame:
    return pd.read_csv(
        caminho,
        dtype=str,
        encoding="utf-8-sig",
    )


atual = ler_csv(ARQUIVO_ATUAL)
atuais = set(
    atual[CHAVE].dropna().str.strip()
)

frames = []

for arquivo in sorted(PASTA_RAW.glob("*.csv")):
    df = ler_csv(arquivo)

    if CHAVE not in df.columns:
        print(f"Ignorado: {arquivo.name} sem {CHAVE}")
        continue

    frames.append(df)

if not frames:
    raise SystemExit("Nenhum CSV bruto válido encontrado.")

brutos = pd.concat(frames, ignore_index=True, sort=False)

brutos[CHAVE] = brutos[CHAVE].astype("string").str.strip()

# Remove linhas sem identificador.
brutos = brutos[
    brutos[CHAVE].notna()
    & brutos[CHAVE].ne("")
].copy()

# Verifica conflitos antes de remover duplicidades.
duplicados = brutos[
    brutos.duplicated(CHAVE, keep=False)
]

if not duplicados.empty:
    print("Existem empenhos repetidos nos arquivos brutos.")
    print(duplicados[[CHAVE]].to_string(index=False))
    raise SystemExit(
        "Carga interrompida para evitar descartar registros."
    )

pendentes = brutos[
    ~brutos[CHAVE].isin(atuais)
].copy()

# Mantém exatamente as colunas e a ordem do CSV atual.
colunas = list(atual.columns)

faltantes = [c for c in colunas if c not in pendentes.columns]
extras = [c for c in pendentes.columns if c not in colunas]

if faltantes or extras:
    print("Diferenças de estrutura identificadas.")
    print("Colunas ausentes nos brutos:", faltantes)
    print("Colunas extras nos brutos:", extras)

for coluna in colunas:
    if coluna not in pendentes.columns:
        pendentes[coluna] = pd.NA

# Todos os registros desta carga são da fonte SP já cadastrada.
pendentes["fonte_id"] = "1"

pendentes = pendentes[colunas]

PASTA_PROCESSED.mkdir(parents=True, exist_ok=True)

pendentes.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    encoding="utf-8-sig",
)

print("\n--- RESULTADO ---")
print(f"Empenhos no CSV processado atual: {len(atuais)}")
print(f"Empenhos únicos nos arquivos brutos: {len(brutos)}")
print(f"Novos empenhos identificados: {len(pendentes)}")
print(f"Arquivo gerado: {ARQUIVO_SAIDA}")
print("\nNenhum dado do banco foi alterado.")
