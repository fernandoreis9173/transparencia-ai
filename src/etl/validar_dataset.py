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
    print("VALIDAÇÃO DO DATASET")
    print("=" * 70)

    if not ARQUIVO.exists():
        print(f"Arquivo não encontrado:")
        print(ARQUIVO)
        return

    df = pd.read_parquet(ARQUIVO)

    print(f"Arquivo: {ARQUIVO}")
    print(f"Registros: {len(df)}")
    print(f"Colunas: {len(df.columns)}")
    print()

    # ---------------------------------------------------------
    # 1. DUPLICIDADES
    # ---------------------------------------------------------

    if "num_empenho" in df.columns:
        duplicados = df[
            df["num_empenho"].duplicated(keep=False)
        ]

        print(f"Empenhos duplicados: {len(duplicados)}")

        if not duplicados.empty:
            print()
            print("Empenhos duplicados:")
            print(
                duplicados[
                    [
                        "num_empenho",
                        "cnpj_cpf_favorecido",
                        "nome_favorecido",
                    ]
                ].to_string(index=False)
            )

    print()

    # ---------------------------------------------------------
    # 2. NULOS
    # ---------------------------------------------------------

    colunas_importantes = [
        "num_empenho",
        "num_processo",
        "cnpj_cpf_favorecido",
        "nome_favorecido",
        "vl_empenhado",
        "vl_liquidado",
        "vl_pago",
    ]

    print("NULOS:")

    for coluna in colunas_importantes:
        if coluna in df.columns:
            quantidade = df[coluna].isna().sum()
            percentual = (
                quantidade / len(df) * 100
                if len(df) > 0
                else 0
            )

            print(
                f"{coluna}: "
                f"{quantidade} "
                f"({percentual:.2f}%)"
            )

    print()

    # ---------------------------------------------------------
    # 3. TIPOS DAS COLUNAS
    # ---------------------------------------------------------

    print("TIPOS DAS COLUNAS:")

    for coluna in df.columns:
        print(f"{coluna}: {df[coluna].dtype}")

    print()

    # ---------------------------------------------------------
    # 4. TOTAIS FINANCEIROS
    # ---------------------------------------------------------

    print("TOTAIS FINANCEIROS:")

    colunas_valor = [
        "vl_empenhado",
        "vl_liquidado",
        "vl_pago",
        "vl_pago_rp",
        "vl_empenhado_inicial",
        "vl_reforco",
        "vl_anulacao",
    ]

    for coluna in colunas_valor:
        if coluna in df.columns:
            total = df[coluna].sum()

            print(
                f"{coluna}: "
                f"R$ {total:,.2f}"
            )

    print()

    # ---------------------------------------------------------
    # 5. ANO
    # ---------------------------------------------------------

    if "ano_exercicio" in df.columns:
        print("ANOS ENCONTRADOS:")

        print(
            df["ano_exercicio"]
            .value_counts()
            .sort_index()
        )

        print()

    # ---------------------------------------------------------
    # 6. ÓRGÃOS
    # ---------------------------------------------------------

    if "cod_orgao" in df.columns:
        print("ÓRGÃOS ENCONTRADOS:")

        print(
            df[
                [
                    "cod_orgao",
                    "nome_orgao",
                ]
            ]
            .drop_duplicates()
            .to_string(index=False)
        )

        print()

    # ---------------------------------------------------------
    # 7. FUNÇÕES
    # ---------------------------------------------------------

    if "cod_funcao" in df.columns:
        print("FUNÇÕES ENCONTRADAS:")

        print(
            df[
                [
                    "cod_funcao",
                    "nome_funcao",
                ]
            ]
            .drop_duplicates()
            .to_string(index=False)
        )

        print()

    # ---------------------------------------------------------
    # 8. EMPENHOS POR FAVORECIDO
    # ---------------------------------------------------------

    if {
        "cnpj_cpf_favorecido",
        "nome_favorecido",
        "num_empenho",
    }.issubset(df.columns):

        print("EMPENHOS POR FAVORECIDO:")

        favorecidos = (
            df.groupby(
                [
                    "cnpj_cpf_favorecido",
                    "nome_favorecido",
                ],
                dropna=False,
            )
            .size()
            .reset_index(name="quantidade_empenhos")
            .sort_values(
                "quantidade_empenhos",
                ascending=False,
            )
        )

        print(
            favorecidos.head(20).to_string(index=False)
        )

        print()

    # ---------------------------------------------------------
    # 9. LIQUIDADO > EMPENHADO
    # ---------------------------------------------------------

    if {
        "vl_empenhado",
        "vl_liquidado",
    }.issubset(df.columns):

        inconsistentes = df[
            df["vl_liquidado"] > df["vl_empenhado"]
        ].copy()

        print("LIQUIDADO MAIOR QUE EMPENHADO:")

        print(
            f"Quantidade: {len(inconsistentes)}"
        )

        if not inconsistentes.empty:

            colunas_exibir = [
                "num_empenho",
                "num_processo",
                "data_registro_empenho",
                "cnpj_cpf_favorecido",
                "nome_favorecido",
                "vl_empenhado",
                "vl_liquidado",
                "vl_pago",
                "vl_empenhado_inicial",
                "vl_reforco",
                "vl_anulacao",
            ]

            colunas_exibir = [
                coluna
                for coluna in colunas_exibir
                if coluna in inconsistentes.columns
            ]

            print()

            print(
                inconsistentes[
                    colunas_exibir
                ]
                .sort_values(
                    "vl_liquidado",
                    ascending=False,
                )
                .head(20)
                .to_string(index=False)
            )

    print()

    # ---------------------------------------------------------
    # 10. RESUMO
    # ---------------------------------------------------------

    print("=" * 70)
    print("VALIDAÇÃO FINALIZADA")
    print("=" * 70)

    print(f"Registros analisados: {len(df)}")
    print(f"Colunas analisadas: {len(df.columns)}")


if __name__ == "__main__":
    main()