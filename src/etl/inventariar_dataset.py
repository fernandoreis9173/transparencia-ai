from pathlib import Path
import pandas as pd


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ARQUIVO_ENTRADA = Path(
    "data/processed/empenhos_2025_orgao_48000_funcao_12.parquet"
)

ARQUIVO_SAIDA = Path(
    "data/output/inventario_colunas.csv"
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def formatar_exemplo(valor):
    """
    Converte um valor para texto para facilitar a visualização
    no CSV de inventário.
    """

    if pd.isna(valor):
        return ""

    return str(valor)


def obter_exemplos(serie, quantidade=3):
    """
    Retorna até 3 valores distintos e não nulos.
    """

    valores = serie.dropna().unique()[:quantidade]

    return [
        formatar_exemplo(valor)
        for valor in valores
    ]


# ============================================================
# INVENTÁRIO
# ============================================================

def gerar_inventario(df):
    registros = []

    total_registros = len(df)

    for coluna in df.columns:

        serie = df[coluna]

        quantidade_nulos = serie.isna().sum()

        percentual_nulos = (
            quantidade_nulos / total_registros * 100
            if total_registros > 0
            else 0
        )

        quantidade_unicos = serie.nunique(
            dropna=True
        )

        exemplos = obter_exemplos(serie)

        registro = {
            "coluna": coluna,
            "tipo": str(serie.dtype),
            "total_registros": total_registros,
            "quantidade_nulos": quantidade_nulos,
            "percentual_nulos": round(percentual_nulos, 2),
            "valores_unicos": quantidade_unicos,
            "exemplo_1": exemplos[0] if len(exemplos) > 0 else "",
            "exemplo_2": exemplos[1] if len(exemplos) > 1 else "",
            "exemplo_3": exemplos[2] if len(exemplos) > 2 else "",
        }

        # ----------------------------------------------------
        # Informações adicionais para colunas numéricas
        # ----------------------------------------------------

        if pd.api.types.is_numeric_dtype(serie):

            registro["minimo"] = (
                serie.min()
                if not serie.dropna().empty
                else ""
            )

            registro["maximo"] = (
                serie.max()
                if not serie.dropna().empty
                else ""
            )

            registro["media"] = (
                serie.mean()
                if not serie.dropna().empty
                else ""
            )

        else:

            registro["minimo"] = ""
            registro["maximo"] = ""
            registro["media"] = ""

        registros.append(registro)

    return pd.DataFrame(registros)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("INVENTÁRIO DO DATASET")
    print("=" * 70)

    # --------------------------------------------------------
    # Verificar arquivo
    # --------------------------------------------------------

    if not ARQUIVO_ENTRADA.exists():

        print(
            f"\nERRO: arquivo não encontrado:\n"
            f"{ARQUIVO_ENTRADA}"
        )

        return

    # --------------------------------------------------------
    # Ler Parquet
    # --------------------------------------------------------

    print(
        f"\nLendo dataset:\n"
        f"{ARQUIVO_ENTRADA}"
    )

    df = pd.read_parquet(ARQUIVO_ENTRADA)

    print("\nDataset carregado.")

    print(f"Registros: {len(df):,}")
    print(f"Colunas:   {len(df.columns)}")

    # --------------------------------------------------------
    # Gerar inventário
    # --------------------------------------------------------

    inventario = gerar_inventario(df)

    # --------------------------------------------------------
    # Criar diretório de saída
    # --------------------------------------------------------

    ARQUIVO_SAIDA.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Salvar CSV
    # --------------------------------------------------------

    inventario.to_csv(
        ARQUIVO_SAIDA,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Resumo
    # --------------------------------------------------------

    print(
        f"\nInventário gerado com sucesso:"
    )

    print(
        f"{ARQUIVO_SAIDA}"
    )

    print("\nResumo:")

    print(
        inventario[
            [
                "coluna",
                "tipo",
                "quantidade_nulos",
                "percentual_nulos",
                "valores_unicos",
            ]
        ].to_string(index=False)
    )

    print("\n" + "=" * 70)
    print("CONCLUÍDO")
    print("=" * 70)


if __name__ == "__main__":
    main()