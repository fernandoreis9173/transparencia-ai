from pathlib import Path

import pandas as pd

from src.api.scripts.despesas_extractor import DespesasExtractor


def main():
    extractor = DespesasExtractor(
        timeout=60,
        max_retries=3,
        delay=0.2,
    )

    resultado = extractor.consultar(
        ano=2025,
        tipo_retorno="favorecido",
        page=1,
        page_size=50,
        cod_orgao=None,
        cod_funcao=None,
    )

    favorecidos = pd.DataFrame(resultado["items"])

    favorecidos["cnpj_cpf_favorecido"] = (
        favorecidos["cnpj_cpf_favorecido"]
        .astype(str)
        .str.replace(r"\D", "", regex=True)
    )

    favorecidos = (
        favorecidos[
            favorecidos["cnpj_cpf_favorecido"].str.len().isin([11, 14])
        ]
        .drop_duplicates(subset=["cnpj_cpf_favorecido"])
        .head(20)
    )

    resultados = []

    for _, favorecido in favorecidos.iterrows():
        documento = favorecido["cnpj_cpf_favorecido"]

        print(f"\nConsultando {documento}...")

        try:
            df = extractor.buscar_empenhos(
                ano=2025,
                cpf_cnpj=documento,
                page_size=50,
                cod_orgao=None,
                cod_funcao=None,
            )

            registro = {
                "documento": documento,
                "quantidade_empenhos": len(df),
                "empenhos_unicos": (
                    df["num_empenho"].nunique()
                    if "num_empenho" in df.columns else 0
                ),
            }

            for campo in [
                "vl_empenhado",
                "vl_liquidado",
                "vl_pago",
            ]:
                valor_api = pd.to_numeric(
                    favorecido[campo], errors="coerce"
                )
                valor_detalhe = (
                    pd.to_numeric(df[campo], errors="coerce").sum()
                    if campo in df.columns else 0
                )

                registro[f"{campo}_api"] = valor_api
                registro[f"{campo}_detalhe"] = valor_detalhe
                registro[f"{campo}_confere"] = (
                    abs(valor_api - valor_detalhe) < 0.01
                )

            resultados.append(registro)

            print(
                f"Empenhos: {len(df)} | "
                f"Valores conferem: "
                f"{all(registro.get(f'{c}_confere', False) for c in ['vl_empenhado', 'vl_liquidado', 'vl_pago'])}"
            )

        except Exception as erro:
            print(f"ERRO: {erro}")

            resultados.append({
                "documento": documento,
                "erro": str(erro),
            })

    comparacao = pd.DataFrame(resultados)

    output = Path("data/output")
    output.mkdir(parents=True, exist_ok=True)

    arquivo = output / "teste_comparacao_20_favorecidos.csv"

    comparacao.to_csv(
        arquivo,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n" + "=" * 60)
    print("RESUMO DA VALIDAÇÃO")
    print("=" * 60)

    colunas_validacao = [
        "vl_empenhado_confere",
        "vl_liquidado_confere",
        "vl_pago_confere",
    ]

    validos = comparacao.dropna(subset=colunas_validacao, how="any")

    print(f"Favorecidos consultados: {len(comparacao)}")
    print(f"Favorecidos comparáveis: {len(validos)}")

    for coluna in colunas_validacao:
        print(f"{coluna}: {validos[coluna].sum()} / {len(validos)}")

    print(f"\nResultado salvo em: {arquivo}")


if __name__ == "__main__":
    main()