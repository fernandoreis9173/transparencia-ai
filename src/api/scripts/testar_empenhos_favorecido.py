from src.api.scripts.despesas_extractor import DespesasExtractor


def main():
    extractor = DespesasExtractor(
        timeout=60,
        max_retries=3,
        delay=0.2,
    )

    cpf_cnpj = "06993919621"

    print("=" * 70)
    print("TESTE DE EXTRAÇÃO DE EMPENHOS INDIVIDUALIZADOS")
    print("=" * 70)

    df = extractor.buscar_empenhos(
        ano=2025,
        cpf_cnpj=cpf_cnpj,
        page_size=50,
        cod_orgao=None,
        cod_funcao=None,
    )

    print(f"\nCPF/CNPJ: {cpf_cnpj}")
    print(f"Empenhos encontrados: {len(df)}")

    if df.empty:
        print("\nNenhum empenho individualizado retornado.")
        return

    print("\nColunas:")
    print(df.columns.tolist())

    print("\nPrimeiros registros:")
    print(df.head(10).to_string(index=False))

    print("\nTotais retornados:")
    for coluna in ["vl_empenhado", "vl_liquidado", "vl_pago"]:
        if coluna in df.columns:
            print(f"{coluna}: {df[coluna].sum():,.2f}")

    if "num_empenho" in df.columns:
        print(
            "Empenhos únicos:",
            df["num_empenho"].nunique()
        )


if __name__ == "__main__":
    main()