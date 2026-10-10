from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

ARQUIVO = (
    BASE_DIR
    / "data"
    / "raw"
    / "favorecidos_2025_orgao_48000_funcao_12.csv"
)


def main():

    df = pd.read_csv(ARQUIVO)

    print("=" * 70)
    print("VALIDAÇÃO DOS FAVORECIDOS")
    print("=" * 70)

    print(f"Total de linhas: {len(df)}")

    print(
        f"CPFs/CNPJs únicos: "
        f"{df['cnpj_cpf_favorecido'].nunique()}"
    )

    print(
        f"CPFs/CNPJs nulos: "
        f"{df['cnpj_cpf_favorecido'].isna().sum()}"
    )

    print(
        f"Nomes nulos: "
        f"{df['nome_favorecido'].isna().sum()}"
    )

    duplicados = df[
        df["cnpj_cpf_favorecido"].duplicated(
            keep=False
        )
    ]

    print(
        f"Registros duplicados por CPF/CNPJ: "
        f"{len(duplicados)}"
    )

    print()
    print("Top 10 favorecidos por valor empenhado:")

    top = df.sort_values(
        "vl_empenhado",
        ascending=False,
    ).head(10)

    print(
        top[
            [
                "cnpj_cpf_favorecido",
                "nome_favorecido",
                "vl_empenhado",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()