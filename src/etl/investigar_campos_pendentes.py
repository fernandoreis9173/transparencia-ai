import requests
import pandas as pd
import os
import json
import time

URL = "https://www.transparencia.sp.gov.br/Despesas/Buscar"

ANO = 2025
COD_ORGAO = 48000
COD_FUNCAO = 12

PAGE_SIZE = 50

OUTPUT_DIR = "data/output"
OUTPUT_CSV = os.path.join(
    OUTPUT_DIR,
    "investigacao_campos_pendentes.csv"
)

OUTPUT_JSON = os.path.join(
    OUTPUT_DIR,
    "investigacao_campos_pendentes_resumo.json"
)


def buscar(payload):
    response = requests.post(
        URL,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    return response.json()


def payload_base(tipo_retorno):
    return {
        "tipoRetorno": tipo_retorno,
        "anoExercicio": ANO,
        "dataInicio": None,
        "dataTermino": None,
        "codigoFiltro": None,
        "nomeFavorecido": None,
        "cpfCnpjFavorecido": None,
        "codOrgao": COD_ORGAO,
        "codFuncao": COD_FUNCAO,
        "codSubfuncao": None,
        "codPrograma": None,
        "codAcao": None,
        "codElemento": None,
        "page": 1,
        "pageSize": PAGE_SIZE,
        "totalItens": 0
    }


def obter_favorecidos():
    payload = payload_base("favorecido")

    resultado = buscar(payload)

    total = resultado.get("totalItems", 0)

    print(f"Total de favorecidos encontrados: {total}")

    return resultado.get("items", [])


def buscar_empenhos_favorecido(cpf_cnpj):
    payload = payload_base("favorecido")

    payload["cpfCnpjFavorecido"] = cpf_cnpj

    payload["page"] = 1

    resultados = []

    while True:

        resultado = buscar(payload)

        items = resultado.get("items", [])

        resultados.extend(items)

        if not resultado.get("hasNext", False):
            break

        payload["page"] += 1

        time.sleep(0.1)

    return resultados


def analisar_registro(item):

    reforco = item.get("vl_reforco")
    anulacao = item.get("vl_anulacao")

    empenhado_inicial = item.get("vl_empenhado_inicial")
    empenhado = item.get("vl_empenhado")

    if reforco is None:
        reforco = 0

    if anulacao is None:
        anulacao = 0

    if empenhado_inicial is not None and empenhado is not None:

        valor_calculado = (
            float(empenhado_inicial)
            + float(reforco)
            - float(anulacao)
        )

        formula_valida = (
            round(valor_calculado, 2)
            == round(float(empenhado), 2)
        )

    else:

        valor_calculado = None
        formula_valida = None

    return {
        "num_empenho": item.get("num_empenho"),
        "ano_exercicio": item.get("ano_exercicio"),
        "cnpj_cpf_favorecido": item.get("cnpj_cpf_favorecido"),
        "nome_favorecido": item.get("nome_favorecido"),

        "cod_orgao": item.get("cod_orgao"),
        "nome_orgao": item.get("nome_orgao"),

        "cod_uo": item.get("cod_uo"),
        "nome_uo": item.get("nome_uo"),

        "cod_funcao": item.get("cod_funcao"),
        "nome_funcao": item.get("nome_funcao"),

        "cod_subfuncao": item.get("cod_subfuncao"),
        "nome_subfuncao": item.get("nome_subfuncao"),

        "cod_programa": item.get("cod_programa"),
        "nome_programa": item.get("nome_programa"),

        "cod_acao": item.get("cod_acao"),
        "nome_acao": item.get("nome_acao"),

        "cod_item": item.get("cod_item"),
        "nome_item": item.get("nome_item"),

        "cod_tipo_licitacao": item.get("cod_tipo_licitacao"),
        "nome_tipo_licitacao": item.get("nome_tipo_licitacao"),

        "indicador_restos": item.get("indicador_restos"),

        "vl_empenhado_inicial": empenhado_inicial,
        "vl_reforco": reforco,
        "vl_anulacao": anulacao,
        "vl_empenhado": empenhado,
        "vl_liquidado": item.get("vl_liquidado"),
        "vl_pago": item.get("vl_pago"),
        "vl_pago_rp": item.get("vl_pago_rp"),

        "valor_calculado": valor_calculado,
        "formula_valida": formula_valida,

        "num_processo": item.get("num_processo"),
        "data_registro_empenho": item.get(
            "data_registro_empenho"
        )
    }


def main():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 70)
    print("INVESTIGAÇÃO DE CAMPOS PENDENTES")
    print("=" * 70)

    print(f"Ano: {ANO}")
    print(f"Órgão: {COD_ORGAO}")
    print(f"Função: {COD_FUNCAO}")
    print()

    favorecidos = obter_favorecidos()

    encontrados = []

    indicador_restos_encontrados = set()

    encontrou_reforco = False
    encontrou_anulacao = False
    encontrou_cod_item = False

    total_empenhos_analisados = 0

    for indice, favorecido in enumerate(favorecidos, start=1):

        cpf_cnpj = (
            favorecido.get("cnpj_cpf_favorecido")
            or favorecido.get("cpf_cnpj_favorecido")
        )

        nome = favorecido.get("nome_favorecido")

        if not cpf_cnpj:
            continue

        print(
            f"[{indice}/{len(favorecidos)}] "
            f"{nome} - {cpf_cnpj}"
        )

        try:

            empenhos = buscar_empenhos_favorecido(cpf_cnpj)

        except Exception as e:

            print(
                f"  ERRO ao consultar favorecido: {e}"
            )

            continue

        for empenho in empenhos:

            total_empenhos_analisados += 1

            registro = analisar_registro(empenho)

            reforco = registro["vl_reforco"]
            anulacao = registro["vl_anulacao"]
            cod_item = registro["cod_item"]
            indicador = registro["indicador_restos"]

            motivo = []

            # -------------------------------------------------
            # 1. REFORÇO
            # -------------------------------------------------

            if reforco is not None and float(reforco) > 0:

                encontrou_reforco = True
                motivo.append("vl_reforco_gt_0")

            # -------------------------------------------------
            # 2. ANULAÇÃO
            # -------------------------------------------------

            if anulacao is not None and float(anulacao) > 0:

                encontrou_anulacao = True
                motivo.append("vl_anulacao_gt_0")

            # -------------------------------------------------
            # 3. INDICADOR RESTOS
            # -------------------------------------------------

            if indicador is not None:

                if indicador not in indicador_restos_encontrados:

                    indicador_restos_encontrados.add(indicador)

                    motivo.append(
                        "novo_indicador_restos"
                    )

            # -------------------------------------------------
            # 4. COD_ITEM
            # -------------------------------------------------

            if cod_item is not None:

                if str(cod_item).strip() != "":

                    encontrou_cod_item = True

                    motivo.append(
                        "cod_item_preenchido"
                    )

            # -------------------------------------------------
            # 5. FÓRMULA
            # -------------------------------------------------

            if registro["formula_valida"] is not None:

                motivo.append(
                    "teste_formula_empenho"
                )

            # -------------------------------------------------
            # GUARDAR
            # -------------------------------------------------

            if motivo:

                registro["motivos"] = ";".join(
                    motivo
                )

                encontrados.append(registro)

        # -----------------------------------------------------
        # CONDIÇÃO DE PARADA
        # -----------------------------------------------------

        # Queremos pelo menos:
        #
        # - um reforço
        # - uma anulação
        # - dois indicadores diferentes
        # - um cod_item
        #
        # Porém continuamos até encontrar todos.

        if (
            encontrou_reforco
            and encontrou_anulacao
            and len(indicador_restos_encontrados) >= 2
            and encontrou_cod_item
        ):

            print()
            print("=" * 70)
            print("TODOS OS CAMPOS PRINCIPAIS FORAM ENCONTRADOS")
            print("=" * 70)

            break

        time.sleep(0.1)

    # ---------------------------------------------------------
    # DATAFRAME
    # ---------------------------------------------------------

    df = pd.DataFrame(encontrados)

    if not df.empty:

        # Remover duplicidades de empenho
        df = df.drop_duplicates(
            subset=["num_empenho"]
        )

        df.to_csv(
            OUTPUT_CSV,
            index=False,
            encoding="utf-8-sig"
        )

    # ---------------------------------------------------------
    # RESUMO
    # ---------------------------------------------------------

    resumo = {

        "ano": ANO,

        "cod_orgao": COD_ORGAO,

        "cod_funcao": COD_FUNCAO,

        "favorecidos_analisados": len(
            favorecidos
        ),

        "empenhos_analisados":
            total_empenhos_analisados,

        "registros_encontrados":
            len(df),

        "encontrou_vl_reforco_gt_0":
            encontrou_reforco,

        "encontrou_vl_anulacao_gt_0":
            encontrou_anulacao,

        "indicadores_restos_encontrados":
            sorted(
                list(
                    indicador_restos_encontrados
                )
            ),

        "quantidade_indicadores_restos":
            len(indicador_restos_encontrados),

        "encontrou_cod_item":
            encontrou_cod_item,

        "formula_testada": True,

        "arquivo_resultado":
            OUTPUT_CSV
    }

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            resumo,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

    print()
    print("=" * 70)
    print("RESULTADO")
    print("=" * 70)

    print(
        f"Favorecidos analisados: "
        f"{len(favorecidos)}"
    )

    print(
        f"Empenhos analisados: "
        f"{total_empenhos_analisados}"
    )

    print(
        f"Registros encontrados: "
        f"{len(df)}"
    )

    print(
        f"vl_reforco > 0: "
        f"{encontrou_reforco}"
    )

    print(
        f"vl_anulacao > 0: "
        f"{encontrou_anulacao}"
    )

    print(
        f"indicador_restos: "
        f"{sorted(indicador_restos_encontrados)}"
    )

    print(
        f"cod_item preenchido: "
        f"{encontrou_cod_item}"
    )

    print()
    print(
        f"CSV: {OUTPUT_CSV}"
    )

    print(
        f"Resumo: {OUTPUT_JSON}"
    )


if __name__ == "__main__":
    main()