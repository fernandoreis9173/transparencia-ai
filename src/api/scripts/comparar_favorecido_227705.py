
import pandas as pd

from src.api.scripts.despesas_extractor import DespesasExtractor


def diagnosticar_duplicidades(df: pd.DataFrame) -> None:
    chave = [
        "ano_exercicio",
        "cod_orgao",
        "cod_uo",
        "num_empenho",
    ]

    print("\n" + "=" * 70)
    print("TESTE DE CHAVES ALTERNATIVAS")
    print("=" * 70)

    chave_com_processo = chave + ["num_processo"]

    if "num_processo" in df.columns:
        print(
            "Chaves distintas incluindo num_processo:",
            df[chave_com_processo].drop_duplicates().shape[0]
        )

        conflitos_processo = df[
            df.duplicated(
                subset=chave_com_processo,
                keep=False
            )
        ]

        print(
            "Linhas repetidas incluindo num_processo:",
            len(conflitos_processo)
        )

        if conflitos_processo.empty:
            print(
                "RESULTADO: nenhuma duplicidade "
                "com a chave incluindo num_processo."
            )
        else:
            print(
                "ATENÇÃO: ainda existem duplicidades "
                "mesmo incluindo num_processo."
            )

            print(
                conflitos_processo[
                    chave_com_processo
                ].to_string(index=False)
            )

    duplicatas_exatas = df[
        df.duplicated(keep=False)
    ]

    print(
        "\nLinhas envolvidas em duplicações "
        "completamente idênticas:",
        len(duplicatas_exatas)
    )

    ausentes = [coluna for coluna in chave if coluna not in df.columns]

    if ausentes:
        print("Colunas ausentes:", ausentes)
        return

    print("Total de linhas:", len(df))
    print("Chaves completas distintas:", df[chave].drop_duplicates().shape[0])

    conflitos = df[df.duplicated(subset=chave, keep=False)]

    print("Linhas envolvidas em chaves repetidas:", len(conflitos))

    if conflitos.empty:
        print("Nenhuma repetição pela chave completa.")
        return

    for identificador, grupo in conflitos.groupby(chave, dropna=False):
        divergentes = [
            coluna
            for coluna in df.columns
            if grupo[coluna].nunique(dropna=False) > 1
        ]

        print("\n" + "-" * 70)
        print("CHAVE:", identificador)
        print("Quantidade de linhas:", len(grupo))
        print("Colunas divergentes:", divergentes)

        colunas = list(dict.fromkeys(chave + divergentes))
        print(grupo[colunas].to_string(index=False))



def main():
    documentos = [
        "10206542000179",
        "50269854000146",
        "51659136000149",
        "96678263000123",
    ]

    extractor = DespesasExtractor(
        timeout=60,
        max_retries=3,
        delay=0.2,
    )

    chave_antiga = [
        "ano_exercicio",
        "cod_orgao",
        "cod_uo",
        "num_empenho",
    ]

    chave_nova = chave_antiga + ["num_processo"]

    for documento in documentos:
        print("\n" + "=" * 75)
        print("FAVORECIDO:", documento)
        print("=" * 75)

        pagina = 1
        registros = []
        total_esperado = None
        total_paginas = None

        try:
            while True:
                resposta = extractor.consultar(
                    ano=2025,
                    tipo_retorno="favorecido",
                    page=pagina,
                    page_size=50,
                    cpf_cnpj_favorecido=documento,
                    cod_orgao=None,
                    cod_funcao=None,
                )

                if total_esperado is None:
                    total_esperado = resposta.get("totalItems")
                    total_paginas = resposta.get("totalPages")

                items = resposta.get("items", [])
                registros.extend(items)

                if pagina >= total_paginas:
                    break

                pagina += 1

            df = pd.DataFrame(registros)

            print("totalItems API:", total_esperado)
            print("Total de páginas:", total_paginas)
            print("Registros recebidos:", len(df))

            if df.empty:
                print("Nenhum registro encontrado.")
                continue

            print(
                "Números de empenho distintos:",
                df["num_empenho"].nunique()
            )

            print(
                "Chaves antigas distintas:",
                df[chave_antiga].drop_duplicates().shape[0]
            )

            print(
                "Chaves novas distintas:",
                df[chave_nova].drop_duplicates().shape[0]
            )

            repeticoes_antigas = df.duplicated(
                subset=chave_antiga,
                keep=False
            ).sum()

            repeticoes_novas = df.duplicated(
                subset=chave_nova,
                keep=False
            ).sum()

            repeticoes_exatas = df.duplicated(
                keep=False
            ).sum()

            print("Linhas repetidas pela chave antiga:", repeticoes_antigas)
            print("Linhas repetidas pela chave nova:", repeticoes_novas)
            print("Linhas completamente idênticas:", repeticoes_exatas)

            if repeticoes_novas == 0:
                print("RESULTADO: chave nova sem conflitos.")
            else:
                print("RESULTADO: ainda existem conflitos.")

                conflitos = df[
                    df.duplicated(
                        subset=chave_nova,
                        keep=False
                    )
                ]

                print(
                    conflitos[chave_nova].to_string(index=False)
                )

        except Exception as erro:
            print("ERRO NA CONSULTA:", type(erro).__name__, str(erro))


if __name__ == "__main__":
    main()
