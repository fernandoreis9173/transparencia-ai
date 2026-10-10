from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_DIR = (
    BASE_DIR
    / "data"
    / "raw"
    / "empenhos"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "empenhos_2025_orgao_48000_funcao_12.parquet"
)


def main():

    print("=" * 70)
    print("CONSOLIDAÇÃO DOS EMPENHOS")
    print("=" * 70)

    arquivos = sorted(
        INPUT_DIR.glob("*.csv")
    )

    print(
        f"Arquivos encontrados: {len(arquivos)}"
    )

    if not arquivos:
        print("Nenhum arquivo encontrado.")
        return

    dfs = []

    for numero, arquivo in enumerate(
        arquivos,
        start=1,
    ):

        print(
            f"[{numero}/{len(arquivos)}] "
            f"{arquivo.name}"
        )

        df = pd.read_csv(
            arquivo,
            dtype={
                "cnpj_cpf_favorecido": str,
                "num_empenho": str,
            },
        )

        dfs.append(df)

    print()
    print("Concatenando dados...")

    df = pd.concat(
        dfs,
        ignore_index=True,
    )

    print(
        f"Registros antes da deduplicação: "
        f"{len(df)}"
    )

    # Remove espaços dos nomes das colunas
    df.columns = (
        df.columns
        .str.strip()
    )

    # Remove espaços dos campos textuais
    colunas_texto = [
        "cnpj_cpf_favorecido",
        "nome_favorecido",
        "num_empenho",
        "num_processo",
        "nome_orgao",
        "nome_uo",
        "nome_funcao",
        "nome_subfuncao",
        "nome_programa",
        "nome_acao",
    ]

    for coluna in colunas_texto:

        if coluna in df.columns:

            df[coluna] = (
                df[coluna]
                .astype("string")
                .str.strip()
            )

    # Deduplicação pelo número do empenho
    antes = len(df)

    df = df.drop_duplicates(
        subset=["num_empenho"],
        keep="first",
    )

    depois = len(df)

    print(
        f"Duplicados removidos: "
        f"{antes - depois}"
    )

    print(
        f"Registros finais: "
        f"{len(df)}"
    )

    # Conversão dos valores monetários
    colunas_valor = [
        "vl_empenhado",
        "vl_liquidado",
        "vl_pago",
        "vl_pago_rp",
        "vl_empenhado_inicial",
        "vl_reforco",
        "vl_anulacao",
        "vl_dotacao_atual",
    ]

    for coluna in colunas_valor:

        if coluna in df.columns:

            df[coluna] = pd.to_numeric(
                df[coluna],
                errors="coerce",
            )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("Salvando Parquet...")

    df.to_parquet(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("=" * 70)
    print("CONSOLIDAÇÃO FINALIZADA")
    print("=" * 70)

    print(
        f"Arquivo: {OUTPUT_FILE}"
    )

    print(
        f"Registros: {len(df)}"
    )

    print(
        f"Colunas: {len(df.columns)}"
    )

    print()
    print("Colunas disponíveis:")

    for coluna in df.columns:
        print(f" - {coluna}")


if __name__ == "__main__":
    main()