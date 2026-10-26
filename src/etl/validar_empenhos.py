from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[3]

PASTA = (
    BASE_DIR
    / "data"
    / "raw"
    / "empenhos"
)


def main():

    arquivos = list(
        PASTA.glob("*.csv")
    )

    print("=" * 70)
    print("VALIDAÇÃO DOS EMPENHOS")
    print("=" * 70)

    print(
        f"Arquivos encontrados: {len(arquivos)}"
    )

    dfs = []

    for arquivo in arquivos:

        df = pd.read_csv(
            arquivo,
            dtype={
                "cnpj_cpf_favorecido": str
            },
        )

        dfs.append(df)

    if not dfs:
        print("Nenhum arquivo encontrado.")
        return

    df = pd.concat(
        dfs,
        ignore_index=True,
    )

    print(
        f"Total de registros: {len(df)}"
    )

    print(
        f"Empenhos únicos: "
        f"{df['num_empenho'].nunique()}"
    )

    duplicados = df[
        df["num_empenho"].duplicated(
            keep=False
        )
    ]

    print(
        f"Registros duplicados: "
        f"{len(duplicados)}"
    )

    print()
    print("Empenhos:")

    colunas = [
        "num_empenho",
        "cnpj_cpf_favorecido",
        "nome_favorecido",
        "vl_empenhado",
        "vl_liquidado",
        "vl_pago",
    ]

    colunas = [
        c for c in colunas
        if c in df.columns
    ]

    print(
        df[colunas].to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()