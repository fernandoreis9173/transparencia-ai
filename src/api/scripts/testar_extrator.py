from pathlib import Path

from api.scripts.despesas_extractor import DespesasExtractor


def main():

    extractor = DespesasExtractor(
        timeout=60,
        max_retries=3,
        delay=0.2,
    )

    # 2M-COMERCIO DE ELETROELETRONICOS LTDA
    cpf_cnpj = "32691514000127"

    df = extractor.buscar_empenhos(
        ano=2025,
        cpf_cnpj=cpf_cnpj,
        page_size=5,
        cod_orgao=48000,
        cod_funcao=12,
    )

    print("\n========== RESULTADO ==========")

    print(f"Total de empenhos: {len(df)}")

    if not df.empty:

        print("\nEmpenhos encontrados:")

        colunas = [
            "num_empenho",
            "data_registro_empenho",
            "vl_empenhado",
            "vl_liquidado",
            "vl_pago",
        ]

        colunas_existentes = [
            coluna
            for coluna in colunas
            if coluna in df.columns
        ]

        print(
            df[colunas_existentes].to_string(
                index=False
            )
        )

    caminho = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "raw"
        / "teste_empenhos_2m.csv"
    )

    extractor.salvar_csv(
        df,
        caminho,
    )


if __name__ == "__main__":
    main()