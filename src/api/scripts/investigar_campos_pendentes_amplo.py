import requests
import pandas as pd
import os
import json
import time


URL = "https://www.transparencia.sp.gov.br/Despesas/Buscar"

ANO = 2025
PAGE_SIZE = 50

OUTPUT_DIR = "data/output"

OUTPUT_CSV = os.path.join(
    OUTPUT_DIR,
    "investigacao_campos_pendentes_amplo.csv"
)

OUTPUT_JSON = os.path.join(
    OUTPUT_DIR,
    "investigacao_campos_pendentes_amplo_resumo.json"
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
        "codOrgao": None,
        "codFuncao": None,
        "codSubfuncao": None,
        "codPrograma": None,
        "codAcao": None,
        "codElemento": None,
        "page": 1,
        "pageSize": PAGE_SIZE,
        "totalItens": 0
    }


# ============================================================
# ÓRGÃOS
# ============================================================

def obter_orgaos():

    payload = payload_base("orgao")

    resultado = buscar(payload)

    items = resultado.get("items", [])

    print(
        f"Órgãos encontrados: {len(items)}"
    )

    return items


# ============================================================
# FAVORECIDOS DE UM ÓRGÃO
# ============================================================

def obter_favorecidos(cod_orgao):

    payload = payload_base("favorecido")

    payload["codOrgao"] = cod_orgao

    todos = []

    pagina = 1

    while True:

        payload["page"] = pagina

        resultado = buscar(payload)

        items = resultado.get("items", [])

        todos.extend(items)

        if not resultado.get("hasNext", False):

            break

        pagina += 1

        time.sleep(0.05)

    return todos


# ============================================================
# EMPENHOS DE UM FAVORECIDO
# ============================================================

def obter_empenhos(
    cpf_cnpj,
    cod_orgao
):

    payload = payload_base("favorecido")

    payload["cpfCnpjFavorecido"] = cpf_cnpj
    payload["codOrgao"] = cod_orgao

    todos = []

    pagina = 1

    while True:

        payload["page"] = pagina

        resultado = buscar(payload)

        items = resultado.get("items", [])

        todos.extend(items)

        if not resultado.get("hasNext", False):

            break

        pagina += 1

        time.sleep(0.05)

    return todos


# ============================================================
# ANALISAR REGISTRO
# ============================================================

def analisar_registro(item):

    reforco = item.get("vl_reforco")
    anulacao = item.get("vl_anulacao")

    inicial = item.get(
        "vl_empenhado_inicial"
    )

    empenhado = item.get(
        "vl_empenhado"
    )

    if reforco is None:
        reforco = 0

    if anulacao is None:
        anulacao = 0

    valor_calculado = None
    formula_valida = None

    if inicial is not None and empenhado is not None:

        valor_calculado = (
            float(inicial)
            + float(reforco)
            - float(anulacao)
        )

        formula_valida = (
            round(valor_calculado, 2)
            == round(float(empenhado), 2)
        )

    motivos = []

    if float(reforco) > 0:

        motivos.append(
            "vl_reforco_gt_0"
        )

    if float(anulacao) > 0:

        motivos.append(
            "vl_anulacao_gt_0"
        )

    if item.get("cod_item") is not None:

        if str(item.get("cod_item")).strip():

            motivos.append(
                "cod_item_preenchido"
            )

    return {
        "num_empenho":
            item.get("num_empenho"),

        "ano_exercicio":
            item.get("ano_exercicio"),

        "cnpj_cpf_favorecido":
            item.get("cnpj_cpf_favorecido"),

        "nome_favorecido":
            item.get("nome_favorecido"),

        "cod_orgao":
            item.get("cod_orgao"),

        "nome_orgao":
            item.get("nome_orgao"),

        "cod_uo":
            item.get("cod_uo"),

        "nome_uo":
            item.get("nome_uo"),

        "cod_funcao":
            item.get("cod_funcao"),

        "nome_funcao":
            item.get("nome_funcao"),

        "cod_subfuncao":
            item.get("cod_subfuncao"),

        "nome_subfuncao":
            item.get("nome_subfuncao"),

        "cod_programa":
            item.get("cod_programa"),

        "nome_programa":
            item.get("nome_programa"),

        "cod_acao":
            item.get("cod_acao"),

        "nome_acao":
            item.get("nome_acao"),

        "cod_item":
            item.get("cod_item"),

        "nome_item":
            item.get("nome_item"),

        "indicador_restos":
            item.get("indicador_restos"),

        "cod_tipo_licitacao":
            item.get("cod_tipo_licitacao"),

        "nome_tipo_licitacao":
            item.get("nome_tipo_licitacao"),

        "vl_empenhado_inicial":
            inicial,

        "vl_reforco":
            reforco,

        "vl_anulacao":
            anulacao,

        "vl_empenhado":
            empenhado,

        "vl_liquidado":
            item.get("vl_liquidado"),

        "vl_pago":
            item.get("vl_pago"),

        "vl_pago_rp":
            item.get("vl_pago_rp"),

        "valor_calculado":
            valor_calculado,

        "formula_valida":
            formula_valida,

        "num_processo":
            item.get("num_processo"),

        "data_registro_empenho":
            item.get(
                "data_registro_empenho"
            ),

        "motivos":
            ";".join(motivos)
    }


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    print("=" * 70)
    print("INVESTIGAÇÃO AMPLA")
    print("=" * 70)

    print(
        f"Ano: {ANO}"
    )

    print()

    # --------------------------------------------------------
    # 1. ÓRGÃOS
    # --------------------------------------------------------

    orgaos = obter_orgaos()

    encontrados = []

    indicadores_restos = set()

    encontrou_reforco = False
    encontrou_anulacao = False
    encontrou_cod_item = False

    total_favorecidos = 0
    total_empenhos = 0

    # --------------------------------------------------------
    # 2. PERCORRER ÓRGÃOS
    # --------------------------------------------------------

    for numero_orgao, orgao in enumerate(
        orgaos,
        start=1
    ):

        cod_orgao = orgao.get(
            "cod_orgao"
        )

        nome_orgao = orgao.get(
            "nome_orgao"
        )

        print()
        print(
            "=" * 70
        )

        print(
            f"ÓRGÃO "
            f"{numero_orgao}/{len(orgaos)}"
        )

        print(
            f"{cod_orgao} - "
            f"{nome_orgao}"
        )

        print(
            "=" * 70
        )

        try:

            favorecidos = obter_favorecidos(
                cod_orgao
            )

        except Exception as erro:

            print(
                f"Erro ao obter favorecidos: "
                f"{erro}"
            )

            continue

        print(
            f"Favorecidos: "
            f"{len(favorecidos)}"
        )

        total_favorecidos += len(
            favorecidos
        )

        # ----------------------------------------------------
        # 3. PERCORRER FAVORECIDOS
        # ----------------------------------------------------

        for numero, favorecido in enumerate(
            favorecidos,
            start=1
        ):

            cpf_cnpj = (
                favorecido.get(
                    "cnpj_cpf_favorecido"
                )
            )

            nome = favorecido.get(
                "nome_favorecido"
            )

            if not cpf_cnpj:

                continue

            print(
                f"[{numero}/{len(favorecidos)}] "
                f"{nome} - {cpf_cnpj}"
            )

            try:

                empenhos = obter_empenhos(
                    cpf_cnpj,
                    cod_orgao
                )

            except Exception as erro:

                print(
                    f"  Erro: {erro}"
                )

                continue

            total_empenhos += len(
                empenhos
            )

            # ------------------------------------------------
            # 4. ANALISAR EMPENHOS
            # ------------------------------------------------

            for item in empenhos:

                registro = analisar_registro(
                    item
                )

                reforco = registro[
                    "vl_reforco"
                ]

                anulacao = registro[
                    "vl_anulacao"
                ]

                cod_item = registro[
                    "cod_item"
                ]

                indicador = registro[
                    "indicador_restos"
                ]

                novo_registro = False

                # --------------------------------------------
                # REFORÇO
                # --------------------------------------------

                if (
                    reforco is not None
                    and float(reforco) > 0
                ):

                    encontrou_reforco = True

                    if (
                        "vl_reforco_gt_0"
                        not in registro["motivos"]
                    ):

                        registro["motivos"] += (
                            ";vl_reforco_gt_0"
                        )

                    novo_registro = True

                # --------------------------------------------
                # ANULAÇÃO
                # --------------------------------------------

                if (
                    anulacao is not None
                    and float(anulacao) > 0
                ):

                    encontrou_anulacao = True

                    if (
                        "vl_anulacao_gt_0"
                        not in registro["motivos"]
                    ):

                        registro["motivos"] += (
                            ";vl_anulacao_gt_0"
                        )

                    novo_registro = True

                # --------------------------------------------
                # INDICADOR RESTOS
                # --------------------------------------------

                if indicador is not None:

                    if indicador not in indicadores_restos:

                        indicadores_restos.add(
                            indicador
                        )

                        registro["motivos"] += (
                            ";novo_indicador_restos"
                        )

                        novo_registro = True

                # --------------------------------------------
                # COD ITEM
                # --------------------------------------------

                if cod_item is not None:

                    if str(cod_item).strip():

                        encontrou_cod_item = True

                        novo_registro = True

                # --------------------------------------------
                # FORMULA
                # --------------------------------------------

                if (
                    registro[
                        "formula_valida"
                    ] is not None
                ):

                    # Guardamos registros para validar
                    # especialmente casos com reforço/anulação.

                    if (
                        float(reforco) > 0
                        or float(anulacao) > 0
                    ):

                        registro["motivos"] += (
                            ";teste_formula_com_movimentacao"
                        )

                        novo_registro = True

                # --------------------------------------------
                # GUARDAR
                # --------------------------------------------

                if novo_registro:

                    encontrados.append(
                        registro
                    )

            # ------------------------------------------------
            # PARADA GLOBAL
            # ------------------------------------------------

            if (
                encontrou_reforco
                and encontrou_anulacao
                and len(indicadores_restos) >= 2
                and encontrou_cod_item
            ):

                print()
                print(
                    "TODOS OS CAMPOS FORAM "
                    "ENCONTRADOS."
                )

                break

            time.sleep(0.05)

        if (
            encontrou_reforco
            and encontrou_anulacao
            and len(indicadores_restos) >= 2
            and encontrou_cod_item
        ):

            break

    # ========================================================
    # RESULTADO
    # ========================================================

    df = pd.DataFrame(
        encontrados
    )

    if not df.empty:

        df = df.drop_duplicates(
            subset=["num_empenho"]
        )

        df.to_csv(
            OUTPUT_CSV,
            index=False,
            encoding="utf-8-sig"
        )

    resumo = {

        "ano": ANO,

        "orgaos_analisados":
            len(orgaos),

        "favorecidos_analisados":
            total_favorecidos,

        "empenhos_analisados":
            total_empenhos,

        "registros_encontrados":
            len(df),

        "encontrou_vl_reforco_gt_0":
            encontrou_reforco,

        "encontrou_vl_anulacao_gt_0":
            encontrou_anulacao,

        "indicadores_restos":
            sorted(
                list(
                    indicadores_restos
                )
            ),

        "quantidade_indicadores_restos":
            len(indicadores_restos),

        "encontrou_cod_item":
            encontrou_cod_item,

        "arquivo":
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
    print("RESULTADO FINAL")
    print("=" * 70)

    print(
        f"Órgãos analisados: "
        f"{len(orgaos)}"
    )

    print(
        f"Favorecidos analisados: "
        f"{total_favorecidos}"
    )

    print(
        f"Empenhos analisados: "
        f"{total_empenhos}"
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
        "indicador_restos: "
        f"{sorted(indicadores_restos)}"
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