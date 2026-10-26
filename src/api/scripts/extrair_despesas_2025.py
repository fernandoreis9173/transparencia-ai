from pathlib import Path
import pandas as pd

from api.scripts.despesas_extractor import DespesasExtractor


ANO = 2025
COD_ORGAO = 48000
COD_FUNCAO = 12

PAGE_SIZE = 50

BASE_DIR = Path(__file__).resolve().parents[3]

RAW_DIR = BASE_DIR / "data" / "raw"

FAVORECIDOS_FILE = (
    RAW_DIR / "favorecidos_2025_orgao_48000_funcao_12.csv"
)


def main():

    print("=" * 70)
    print("EXTRAÇÃO DE FAVORECIDOS")
    print("=" * 70)

    extractor = DespesasExtractor(
        timeout=60,
        max_retries=3,
        delay=0.2,
    )

    df = extractor.buscar_favorecidos(
        ano=ANO,
        page_size=PAGE_SIZE,
        cod_orgao=COD_ORGAO,
        cod_funcao=COD_FUNCAO,
    )

    print()
    print(f"Favorecidos encontrados: {len(df)}")

    if df.empty:
        print("Nenhum favorecido encontrado.")
        return

    print()
    print("Colunas:")
    print(df.columns.tolist())

    print()
    print("Primeiros registros:")
    print(df.head())

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        FAVORECIDOS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print(f"Arquivo salvo em:")
    print(FAVORECIDOS_FILE)


if __name__ == "__main__":
    main()