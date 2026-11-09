import pandas as pd

from src.api.scripts.despesas_extractor import DespesasExtractor


def main():
    extractor = DespesasExtractor(
        timeout=60,
        max_retries=3,
        delay=0.2,
    )

    documento = "22770554000100"

    resultado = extractor.consultar(
        ano=2025,
        tipo_retorno="favorecido",
        page=1,
        page_size=50,
        cpf_cnpj_favorecido=documento,
        cod_orgao=None,
        cod_funcao=None,
    )

    itens = resultado["items"]
    df = pd.DataFrame(itens)

    print("=" * 60)
    print("DIAGNÓSTICO DO FAVORECIDO")
    print("=" * 60)

    print("Documento:", documento)
    print("Total informado pela API:", resultado["totalItems"])
    print("Total de páginas:", resultado.get("totalPages"))
    print("Registros recebidos:", len(df))

    if df.empty:
        return

    print("\nEmpenhos:")
    print(
        df[[
            "num_empenho",
            "cod_orgao",
            "cod_uo",
            "vl_empenhado",
            "vl_liquidado",
            "vl_pago",
        ]].to_string(index=False)
    )

    print("\nEmpenhos duplicados:")
    print(
        df[df.duplicated(subset=["num_empenho"], keep=False)]
        [["num_empenho", "cod_orgao", "cod_uo"]]
        .to_string(index=False)
    )

    print("\nTotais:")
    for campo in ["vl_empenhado", "vl_liquidado", "vl_pago"]:
        print(f"{campo}: {pd.to_numeric(df[campo], errors='coerce').sum():,.2f}")

    print("\nQuantidade de empenhos únicos:")
    print(df["num_empenho"].nunique())

    df.to_csv(
        "data/output/diagnostico_22770554000100.csv",
        index=False,
        encoding="utf-8-sig",
    )


if __name__ == "__main__":
    main()