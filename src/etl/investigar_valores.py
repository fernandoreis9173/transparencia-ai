from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

ARQUIVO = (
    BASE_DIR
    / "data"
    / "processed"
    / "empenhos_2025_orgao_48000_funcao_12.parquet"
)


def main():
    print("=" * 70)
    print("INVESTIGAÇÃO DOS VALORES DOS EMPENHOS")
    print("=" * 70)

    df = pd.read_parquet(ARQUIVO)

    # ---------------------------------------------------------
    # REGISTROS COM LIQUIDADO > EMPENHADO
    # ---------------------------------------------------------

    df_problemas = df[
        df["vl_liquidado"] > df["vl_empenhado"]
    ].copy()

    print(f"\nRegistros investigados: {len(df_problemas)}")

    colunas = [
        "num_empenho",
        "num_processo",
        "data_registro_empenho",
        "cnpj_cpf_favorecido",
        "nome_favorecido",

        "vl_empenhado",
        "vl_liquidado",
        "vl_pago",
        "vl_pago_rp",

        "vl_empenhado_inicial",
        "vl_reforco",
        "vl_anulacao",

        "cod_orgao",
        "cod_uo",
        "cod_funcao",
        "cod_subfuncao",
        "cod_programa",
        "cod_acao",
        "cod_elemento",
        "cod_fonte",

        "nome_orgao",
        "nome_uo",
        "nome_funcao",
        "nome_subfuncao",
        "nome_programa",
        "nome_acao",

        "indicador_restos",
    ]

    colunas = [
        coluna
        for coluna in colunas
        if coluna in df_problemas.columns
    ]

    print("\nREGISTROS:")
    print(
        df_problemas[colunas]
        .sort_values(
            "vl_liquidado",
            ascending=False,
        )
        .to_string(index=False)
    )

    # ---------------------------------------------------------
    # DIFERENÇA
    # ---------------------------------------------------------

    df_problemas["diferenca"] = (
        df_problemas["vl_liquidado"]
        - df_problemas["vl_empenhado"]
    )

    df_problemas["multiplicador"] = (
        df_problemas["vl_liquidado"]
        / df_problemas["vl_empenhado"]
    )

    print("\n")
    print("ANÁLISE DA DIFERENÇA:")
    print(
        df_problemas[
            [
                "num_empenho",
                "vl_empenhado",
                "vl_liquidado",
                "diferenca",
                "multiplicador",
            ]
        ]
        .sort_values(
            "multiplicador",
            ascending=False,
        )
        .to_string(index=False)
    )

    # ---------------------------------------------------------
    # PROCESSOS
    # ---------------------------------------------------------

    print("\n")
    print("PROCESSOS ENVOLVIDOS:")

    print(
        df_problemas[
            [
                "num_processo",
                "num_empenho",
                "nome_favorecido",
            ]
        ]
        .sort_values("num_processo")
        .to_string(index=False)
    )

    # ---------------------------------------------------------
    # FAVORECIDOS
    # ---------------------------------------------------------

    print("\n")
    print("FAVORECIDOS ENVOLVIDOS:")

    print(
        df_problemas[
            [
                "cnpj_cpf_favorecido",
                "nome_favorecido",
            ]
        ]
        .drop_duplicates()
        .to_string(index=False)
    )

    print("\n")
    print("=" * 70)
    print("FIM DA INVESTIGAÇÃO")
    print("=" * 70)


if __name__ == "__main__":
    main()