import json
import os
import random
import time
from datetime import datetime

import pandas as pd
import requests


# ============================================================
# CONFIGURAÇÃO
# ============================================================

URL = "https://www.transparencia.sp.gov.br/Despesas/Buscar"

ANO = 2025
PAGE_SIZE = 50

OUTPUT_DIR = "data/output"

CSV_SAIDA = os.path.join(
    OUTPUT_DIR,
    "investigacao_campos_pendentes_v2.csv"
)

JSON_SAIDA = os.path.join(
    OUTPUT_DIR,
    "investigacao_campos_pendentes_v2_resumo.json"
)

CHECKPOINT = os.path.join(
    OUTPUT_DIR,
    "investigacao_campos_pendentes_v2_checkpoint.json"
)

# ============================================================
# TAMANHOS PROGRESSIVOS
# ============================================================
#
# A investigação começa pequena.
#
# Se não encontrar as evidências necessárias:
#
# 100 -> 250 -> 500 -> 1000
#
# Isso evita milhares de requisições desnecessárias.
# ============================================================

NIVEIS_BUSCA = [
    100,
    250,
    500,
    1000
]

# Quantos candidatos de cada órgão entram
# inicialmente na seleção.
CANDIDATOS_POR_ORGAO = 10

# Número de candidatos aleatórios adicionais.
AMOSTRA_ALEATORIA = 20

# Pausa entre requisições.
SLEEP = 0.05

TIMEOUT = 60

# Seed fixa para a amostra ser reproduzível.
RANDOM_SEED = 2025


# ============================================================
# SESSION HTTP
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/154.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json"
})


# ============================================================
# CONTADORES
# ============================================================

stats = {
    "requisicoes": 0,
    "erros": 0,
    "inicio": None
}


# ============================================================
# UTILIDADES
# ============================================================

def agora():
    return datetime.now().isoformat(
        timespec="seconds"
    )


def numero(valor):

    if valor is None:
        return 0.0

    try:
        return float(valor)

    except Exception:
        return 0.0


def salvar_json(caminho, dados):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    with open(
        caminho,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# CHECKPOINT
# ============================================================

def checkpoint_vazio():

    return {
        "versao": "v2",
        "ano": ANO,
        "ultima_atualizacao": agora(),

        "nivel_atual": 100,

        "candidatos_processados": [],

        "evidencias": [],

        "estatisticas": {
            "requisicoes": 0,
            "erros": 0
        }
    }


def carregar_checkpoint():

    if not os.path.exists(CHECKPOINT):

        print(
            "ℹ️ Nenhum checkpoint encontrado."
        )

        return checkpoint_vazio()

    try:

        with open(
            CHECKPOINT,
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(arquivo)

        print(
            "✓ Checkpoint encontrado."
        )

        print(
            f"  Candidatos já processados: "
            f"{len(dados.get('candidatos_processados', []))}"
        )

        print(
            f"  Evidências salvas: "
            f"{len(dados.get('evidencias', []))}"
        )

        return dados

    except Exception as erro:

        print(
            f"⚠️ Erro ao carregar checkpoint: {erro}"
        )

        print(
            "Criando checkpoint novo."
        )

        return checkpoint_vazio()


def salvar_checkpoint(
    candidatos_processados,
    evidencias,
    nivel_atual
):

    dados = {
        "versao": "v2",
        "ano": ANO,
        "ultima_atualizacao": agora(),

        "nivel_atual": nivel_atual,

        "candidatos_processados":
            sorted(
                candidatos_processados
            ),

        "evidencias":
            evidencias,

        "estatisticas": stats
    }

    salvar_json(
        CHECKPOINT,
        dados
    )


# ============================================================
# REQUISIÇÃO POST
# ============================================================

def buscar(payload):

    for tentativa in range(1, 4):

        try:

            stats["requisicoes"] += 1

            resposta = session.post(
                URL,
                json=payload,
                timeout=TIMEOUT
            )

            resposta.raise_for_status()

            return resposta.json()

        except Exception as erro:

            stats["erros"] += 1

            print(
                f"⚠️ Erro "
                f"{tentativa}/3: {erro}"
            )

            time.sleep(2)

    return None


# ============================================================
# PAYLOAD
# ============================================================

def payload_base(tipo_retorno):

    return {

        "tipoRetorno":
            tipo_retorno,

        "anoExercicio":
            ANO,

        "dataInicio":
            None,

        "dataTermino":
            None,

        "codigoFiltro":
            None,

        "nomeFavorecido":
            None,

        "cpfCnpjFavorecido":
            None,

        "codOrgao":
            None,

        "codFuncao":
            None,

        "codSubfuncao":
            None,

        "codPrograma":
            None,

        "codAcao":
            None,

        "codElemento":
            None,

        "page":
            1,

        "pageSize":
            PAGE_SIZE,

        "totalItens":
            0
    }


# ============================================================
# BUSCAR ÓRGÃOS
# ============================================================

def obter_orgaos():

    print(
        "\n🔎 Buscando órgãos..."
    )

    payload = payload_base(
        "orgao"
    )

    resposta = buscar(
        payload
    )

    if not resposta:

        return []

    items = resposta.get(
        "items",
        []
    )

    print(
        f"✓ {len(items)} órgãos encontrados."
    )

    return items


# ============================================================
# BUSCAR FAVORECIDOS
# ============================================================

def obter_favorecidos(
    cod_orgao
):

    payload = payload_base(
        "favorecido"
    )

    payload["codOrgao"] = cod_orgao

    payload["page"] = 1

    resposta = buscar(
        payload
    )

    if not resposta:

        return []

    primeira_pagina = resposta.get(
        "items",
        []
    )

    total = resposta.get(
        "totalItems",
        0
    )

    total_pages = resposta.get(
        "totalPages",
        1
    )

    # --------------------------------------------------------
    # IMPORTANTE
    #
    # Não precisamos baixar todas as páginas.
    #
    # Pegamos somente algumas páginas por órgão para montar
    # os candidatos iniciais.
    # --------------------------------------------------------

    max_paginas = min(
        total_pages,
        5
    )

    items = list(
        primeira_pagina
    )

    for pagina in range(
        2,
        max_paginas + 1
    ):

        payload["page"] = pagina

        resposta_pagina = buscar(
            payload
        )

        if not resposta_pagina:
            continue

        items.extend(
            resposta_pagina.get(
                "items",
                []
            )
        )

        time.sleep(
            SLEEP
        )

    print(
        f"   Órgão {cod_orgao}: "
        f"{total:,} favorecidos "
        f"| carregados: {len(items)}"
    )

    return items


# ============================================================
# SCORE DO CANDIDATO
# ============================================================

def calcular_score(item):

    empenhado = numero(
        item.get(
            "vl_empenhado"
        )
    )

    liquidado = numero(
        item.get(
            "vl_liquidado"
        )
    )

    pago = numero(
        item.get(
            "vl_pago"
        )
    )

    # Diferença que pode indicar comportamento
    # interessante para investigação.
    diferenca_liquidado = max(
        0,
        liquidado - empenhado
    )

    score = (

        empenhado * 1.0

        +

        liquidado * 0.5

        +

        pago * 0.25

        +

        diferenca_liquidado * 5.0
    )

    return score


# ============================================================
# SELEÇÃO DOS CANDIDATOS
# ============================================================

def selecionar_candidatos(
    favorecidos,
    limite
):

    if not favorecidos:

        return []

    # --------------------------------------------------------
    # Remove CPFs/CNPJs vazios
    # --------------------------------------------------------

    validos = []

    for item in favorecidos:

        cpf = item.get(
            "cnpj_cpf_favorecido"
        )

        if not cpf:
            continue

        item = dict(item)

        item["_score"] = (
            calcular_score(item)
        )

        validos.append(
            item
        )

    if not validos:

        return []

    # --------------------------------------------------------
    # Ordena por score
    # --------------------------------------------------------

    validos.sort(
        key=lambda x:
        x["_score"],
        reverse=True
    )

    selecionados = []

    # --------------------------------------------------------
    # 1. Maiores valores
    # --------------------------------------------------------

    quantidade_top = min(
        limite // 2,
        len(validos)
    )

    selecionados.extend(
        validos[:quantidade_top]
    )

    # --------------------------------------------------------
    # 2. Diversificação
    #
    # Pegamos alguns candidatos de posições diferentes
    # da lista para evitar viés.
    # --------------------------------------------------------

    restantes = [
        x
        for x in validos
        if x not in selecionados
    ]

    random.seed(
        RANDOM_SEED
    )

    quantidade_random = min(
        AMOSTRA_ALEATORIA,
        len(restantes)
    )

    if quantidade_random > 0:

        selecionados.extend(
            random.sample(
                restantes,
                quantidade_random
            )
        )

    # --------------------------------------------------------
    # 3. Completar pelo ranking
    # --------------------------------------------------------

    for item in validos:

        if len(selecionados) >= limite:
            break

        if item not in selecionados:

            selecionados.append(
                item
            )

    return selecionados[:limite]


# ============================================================
# CONSULTAR EMPENHOS
# ============================================================

def obter_empenhos(
    cpf_cnpj,
    cod_orgao
):

    payload = payload_base(
        "favorecido"
    )

    payload[
        "cpfCnpjFavorecido"
    ] = cpf_cnpj

    payload[
        "codOrgao"
    ] = cod_orgao

    resposta = buscar(
        payload
    )

    if not resposta:

        return []

    return resposta.get(
        "items",
        []
    )


# ============================================================
# ANALISAR EMPENHO
# ============================================================

def analisar_registro(
    item
):

    inicial = numero(
        item.get(
            "vl_empenhado_inicial"
        )
    )

    reforco = numero(
        item.get(
            "vl_reforco"
        )
    )

    anulacao = numero(
        item.get(
            "vl_anulacao"
        )
    )

    empenhado = numero(
        item.get(
            "vl_empenhado"
        )
    )

    liquidado = numero(
        item.get(
            "vl_liquidado"
        )
    )

    pago = numero(
        item.get(
            "vl_pago"
        )
    )

    formula_calculada = (
        inicial
        + reforco
        - anulacao
    )

    formula_ok = (
        abs(
            formula_calculada
            - empenhado
        )
        < 0.01
    )

    motivos = []

    if abs(reforco) > 0.001:

        motivos.append(
            "vl_reforco"
        )

    if abs(anulacao) > 0.001:

        motivos.append(
            "vl_anulacao"
        )

    if item.get(
        "cod_item"
    ) not in (
        None,
        "",
        0,
        "0"
    ):

        motivos.append(
            "cod_item"
        )

    indicador = item.get(
        "indicador_restos"
    )

    if indicador not in (
        None,
        ""
    ):

        motivos.append(
            "indicador_restos"
        )

    if liquidado > empenhado + 0.01:

        motivos.append(
            "liquidado_maior_empenhado"
        )

    return {

        "num_empenho":
            item.get(
                "num_empenho"
            ),

        "cnpj_cpf_favorecido":
            item.get(
                "cnpj_cpf_favorecido"
            ),

        "nome_favorecido":
            item.get(
                "nome_favorecido"
            ),

        "cod_orgao":
            item.get(
                "cod_orgao"
            ),

        "nome_orgao":
            item.get(
                "nome_orgao"
            ),

        "cod_uo":
            item.get(
                "cod_uo"
            ),

        "cod_funcao":
            item.get(
                "cod_funcao"
            ),

        "cod_subfuncao":
            item.get(
                "cod_subfuncao"
            ),

        "cod_programa":
            item.get(
                "cod_programa"
            ),

        "cod_acao":
            item.get(
                "cod_acao"
            ),

        "vl_empenhado_inicial":
            inicial,

        "vl_reforco":
            reforco,

        "vl_anulacao":
            anulacao,

        "vl_empenhado":
            empenhado,

        "vl_liquidado":
            liquidado,

        "vl_pago":
            pago,

        "vl_pago_rp":
            numero(
                item.get(
                    "vl_pago_rp"
                )
            ),

        "cod_item":
            item.get(
                "cod_item"
            ),

        "nome_item":
            item.get(
                "nome_item"
            ),

        "cod_tipo_licitacao":
            item.get(
                "cod_tipo_licitacao"
            ),

        "nome_tipo_licitacao":
            item.get(
                "nome_tipo_licitacao"
            ),

        "cod_fonte_detalhada":
            item.get(
                "cod_fonte_detalhada"
            ),

        "indicador_restos":
            indicador,

        "num_processo":
            item.get(
                "num_processo"
            ),

        "data_registro_empenho":
            item.get(
                "data_registro_empenho"
            ),

        "formula_calculada":
            formula_calculada,

        "formula_ok":
            formula_ok,

        "motivos":
            ",".join(
                motivos
            ),

        "ultima_atualizacao_api":
            item.get(
                "ultimaAtualizacao"
            )
    }


# ============================================================
# VERIFICAR SE É EVIDÊNCIA
# ============================================================

def e_evidencia(
    registro
):

    return any([

        abs(
            numero(
                registro[
                    "vl_reforco"
                ]
            )
        ) > 0.001,

        abs(
            numero(
                registro[
                    "vl_anulacao"
                ]
            )
        ) > 0.001,

        registro[
            "cod_item"
        ] not in (
            None,
            "",
            0,
            "0"
        ),

        registro[
            "indicador_restos"
        ] not in (
            None,
            ""
        ),

        registro[
            "vl_liquidado"
        ]
        >
        registro[
            "vl_empenhado"
        ] + 0.01
    ])


# ============================================================
# ESTADO DAS EVIDÊNCIAS
# ============================================================

def analisar_estado(
    evidencias
):

    encontrou_reforco = any(
        numero(
            x.get(
                "vl_reforco"
            )
        ) > 0
        for x in evidencias
    )

    encontrou_anulacao = any(
        numero(
            x.get(
                "vl_anulacao"
            )
        ) > 0
        for x in evidencias
    )

    encontrou_cod_item = any(
        x.get(
            "cod_item"
        ) not in (
            None,
            "",
            0,
            "0"
        )
        for x in evidencias
    )

    indicadores = sorted(
        set(
            x.get(
                "indicador_restos"
            )
            for x in evidencias
            if x.get(
                "indicador_restos"
            ) not in (
                None,
                ""
            )
        )
    )

    movimentacoes = [

        x

        for x in evidencias

        if (
            numero(
                x.get(
                    "vl_reforco"
                )
            ) != 0

            or

            numero(
                x.get(
                    "vl_anulacao"
                )
            ) != 0
        )
    ]

    formula_ok = [

        x

        for x in movimentacoes

        if x.get(
            "formula_ok"
        )
    ]

    return {

        "reforco":
            encontrou_reforco,

        "anulacao":
            encontrou_anulacao,

        "cod_item":
            encontrou_cod_item,

        "indicadores_restos":
            indicadores,

        "quantidade_indicadores":
            len(indicadores),

        "movimentacoes":
            len(movimentacoes),

        "formula_ok_movimentacoes":
            len(formula_ok)
    }


# ============================================================
# CRITÉRIO DE PARADA
# ============================================================
#
# Não exigimos todos os critérios para parar.
#
# A investigação pode terminar se encontrarmos evidência
# forte suficiente para documentar os campos.
#
# ============================================================

def pode_parar(
    evidencias
):

    estado = analisar_estado(
        evidencias
    )

    # Caso ideal:
    if (
        estado["reforco"]
        and
        estado["anulacao"]
        and
        estado["cod_item"]
        and
        estado["quantidade_indicadores"] >= 2
    ):

        return True

    return False


# ============================================================
# GERAR RESUMO
# ============================================================

def gerar_resumo(
    evidencias,
    candidatos_processados
):

    estado = analisar_estado(
        evidencias
    )

    return {

        "versao":
            "v2",

        "ano":
            ANO,

        "gerado_em":
            agora(),

        "candidatos_processados":
            len(
                candidatos_processados
            ),

        "evidencias":
            len(
                evidencias
            ),

        "requisicoes_http":
            stats[
                "requisicoes"
            ],

        "erros_http":
            stats[
                "erros"
            ],

        "reforco_encontrado":
            estado[
                "reforco"
            ],

        "anulacao_encontrada":
            estado[
                "anulacao"
            ],

        "cod_item_encontrado":
            estado[
                "cod_item"
            ],

        "indicadores_restos":
            estado[
                "indicadores_restos"
            ],

        "quantidade_indicadores_restos":
            estado[
                "quantidade_indicadores"
            ],

        "empenhos_com_movimentacao":
            estado[
                "movimentacoes"
            ],

        "formula_ok_com_movimentacao":
            estado[
                "formula_ok_movimentacoes"
            ],

        "criterio_parada":
            pode_parar(
                evidencias
            )
    }


# ============================================================
# SALVAR RESULTADOS
# ============================================================

def salvar_resultados(
    evidencias,
    candidatos_processados
):

    if evidencias:

        df = pd.DataFrame(
            evidencias
        )

        # Remove duplicados pelo número do empenho.
        if (
            "num_empenho"
            in df.columns
        ):

            df = df.drop_duplicates(
                subset=[
                    "num_empenho"
                ]
            )

        df.to_csv(
            CSV_SAIDA,
            index=False,
            encoding="utf-8-sig"
        )

    resumo = gerar_resumo(
        evidencias,
        candidatos_processados
    )

    salvar_json(
        JSON_SAIDA,
        resumo
    )

    return resumo


# ============================================================
# MAIN
# ============================================================

def main():

    stats["inicio"] = time.time()

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    checkpoint = carregar_checkpoint()

    candidatos_processados = set(
        checkpoint.get(
            "candidatos_processados",
            []
        )
    )

    evidencias = checkpoint.get(
        "evidencias",
        []
    )

    nivel_checkpoint = checkpoint.get(
        "nivel_atual",
        100
    )

    print()
    print("=" * 75)
    print(
        "INVESTIGAÇÃO DE CAMPOS PENDENTES - V2 DEFINITIVA"
    )
    print("=" * 75)

    print(
        f"Ano: {ANO}"
    )

    print(
        f"Início: {agora()}"
    )

    print(
        f"Candidatos já processados: "
        f"{len(candidatos_processados)}"
    )

    print(
        f"Evidências já encontradas: "
        f"{len(evidencias)}"
    )

    # --------------------------------------------------------
    # 1. ÓRGÃOS
    # --------------------------------------------------------

    orgaos = obter_orgaos()

    if not orgaos:

        print(
            "❌ Não foi possível obter os órgãos."
        )

        return

    # --------------------------------------------------------
    # 2. COLETAR CANDIDATOS
    # --------------------------------------------------------

    todos_candidatos = []

    print()
    print(
        "🔎 Montando candidatos..."
    )

    for indice, orgao in enumerate(
        orgaos,
        1
    ):

        cod_orgao = orgao.get(
            "cod_orgao"
        )

        nome_orgao = orgao.get(
            "nome_orgao"
        )

        print(
            f"\n[{indice}/{len(orgaos)}] "
            f"{nome_orgao}"
        )

        favorecidos = obter_favorecidos(
            cod_orgao
        )

        # ----------------------------------------------------
        # Seleciona candidatos daquele órgão.
        # ----------------------------------------------------

        candidatos_orgao = (
            selecionar_candidatos(
                favorecidos,
                CANDIDATOS_POR_ORGAO
            )
        )

        for candidato in candidatos_orgao:

            candidato[
                "_cod_orgao"
            ] = cod_orgao

            candidato[
                "_nome_orgao"
            ] = nome_orgao

            todos_candidatos.append(
                candidato
            )

    # --------------------------------------------------------
    # 3. REMOVER DUPLICADOS
    # --------------------------------------------------------

    mapa = {}

    for candidato in todos_candidatos:

        cpf = candidato.get(
            "cnpj_cpf_favorecido"
        )

        orgao = candidato.get(
            "_cod_orgao"
        )

        if not cpf:
            continue

        chave = (
            str(orgao)
            + "|"
            + str(cpf)
        )

        mapa[chave] = candidato

    todos_candidatos = list(
        mapa.values()
    )

    # --------------------------------------------------------
    # 4. ORDENAR
    # --------------------------------------------------------

    todos_candidatos.sort(
        key=lambda x:
        x.get(
            "_score",
            0
        ),
        reverse=True
    )

    print()
    print("=" * 75)

    print(
        f"✓ Candidatos disponíveis: "
        f"{len(todos_candidatos)}"
    )

    print("=" * 75)

    # --------------------------------------------------------
    # 5. NÍVEIS PROGRESSIVOS
    # --------------------------------------------------------

    for nivel in NIVEIS_BUSCA:

        if nivel < nivel_checkpoint:
            continue

        print()
        print("=" * 75)

        print(
            f"🔬 NÍVEL DE INVESTIGAÇÃO: "
            f"{nivel} candidatos"
        )

        print("=" * 75)

        candidatos_nivel = (
            todos_candidatos[
                :nivel
            ]
        )

        for indice, candidato in enumerate(
            candidatos_nivel,
            1
        ):

            cpf = candidato.get(
                "cnpj_cpf_favorecido"
            )

            cod_orgao = candidato.get(
                "_cod_orgao"
            )

            nome = candidato.get(
                "nome_favorecido"
            )

            chave = (
                str(cod_orgao)
                + "|"
                + str(cpf)
            )

            # ------------------------------------------------
            # Já pesquisado?
            # ------------------------------------------------

            if chave in candidatos_processados:

                continue

            print(
                f"[{indice}/{nivel}] "
                f"{nome} - {cpf}"
            )

            # ------------------------------------------------
            # Consulta individual
            # ------------------------------------------------

            empenhos = obter_empenhos(
                cpf,
                cod_orgao
            )

            print(
                f"    → "
                f"{len(empenhos)} empenho(s)"
            )

            for item in empenhos:

                registro = (
                    analisar_registro(
                        item
                    )
                )

                if e_evidencia(
                    registro
                ):

                    # Evita duplicidade
                    num_empenho = (
                        registro[
                            "num_empenho"
                        ]
                    )

                    ja_existe = any(
                        x.get(
                            "num_empenho"
                        )
                        == num_empenho

                        for x in evidencias
                    )

                    if not ja_existe:

                        evidencias.append(
                            registro
                        )

                        print()
                        print(
                            "    ⭐ "
                            "EVIDÊNCIA ENCONTRADA"
                        )

                        print(
                            f"       Empenho: "
                            f"{registro['num_empenho']}"
                        )

                        print(
                            f"       Favorecido: "
                            f"{registro['nome_favorecido']}"
                        )

                        print(
                            f"       Motivos: "
                            f"{registro['motivos']}"
                        )

                        print(
                            f"       Empenhado: "
                            f"{registro['vl_empenhado']}"
                        )

                        print(
                            f"       Liquidado: "
                            f"{registro['vl_liquidado']}"
                        )

                        print(
                            f"       Reforço: "
                            f"{registro['vl_reforco']}"
                        )

                        print(
                            f"       Anulação: "
                            f"{registro['vl_anulacao']}"
                        )

                        print(
                            f"       Item: "
                            f"{registro['cod_item']}"
                        )

                        print(
                            f"       Restos: "
                            f"{registro['indicador_restos']}"
                        )

            # ------------------------------------------------
            # Marca como processado
            # ------------------------------------------------

            candidatos_processados.add(
                chave
            )

            # ------------------------------------------------
            # Salva imediatamente
            # ------------------------------------------------

            salvar_checkpoint(
                candidatos_processados,
                evidencias,
                nivel
            )

            # ------------------------------------------------
            # Verifica parada
            # ------------------------------------------------

            if pode_parar(
                evidencias
            ):

                print()
                print("=" * 75)

                print(
                    "🎯 CRITÉRIOS PRINCIPAIS "
                    "ENCONTRADOS!"
                )

                print("=" * 75)

                resumo = salvar_resultados(
                    evidencias,
                    candidatos_processados
                )

                print(
                    json.dumps(
                        resumo,
                        ensure_ascii=False,
                        indent=2
                    )
                )

                return

            time.sleep(
                SLEEP
            )

        # ----------------------------------------------------
        # Terminou um nível
        # ----------------------------------------------------

        resumo = salvar_resultados(
            evidencias,
            candidatos_processados
        )

        print()
        print(
            "📊 Resultado do nível:"
        )

        print(
            f"   Requisições HTTP: "
            f"{stats['requisicoes']}"
        )

        print(
            f"   Candidatos processados: "
            f"{len(candidatos_processados)}"
        )

        print(
            f"   Evidências: "
            f"{len(evidencias)}"
        )

        print(
            f"   Reforço: "
            f"{resumo['reforco_encontrado']}"
        )

        print(
            f"   Anulação: "
            f"{resumo['anulacao_encontrada']}"
        )

        print(
            f"   cod_item: "
            f"{resumo['cod_item_encontrado']}"
        )

        print(
            f"   Indicadores de restos: "
            f"{resumo['indicadores_restos']}"
        )

        # Atualiza checkpoint para próximo nível
        salvar_checkpoint(
            candidatos_processados,
            evidencias,
            nivel + 1
        )

    # ========================================================
    # FINAL
    # ========================================================

    resumo = salvar_resultados(
        evidencias,
        candidatos_processados
    )

    print()
    print("=" * 75)
    print(
        "🏁 INVESTIGAÇÃO FINALIZADA"
    )
    print("=" * 75)

    print(
        f"Favorecidos processados: "
        f"{len(candidatos_processados)}"
    )

    print(
        f"Evidências encontradas: "
        f"{len(evidencias)}"
    )

    print(
        f"Requisições HTTP: "
        f"{stats['requisicoes']}"
    )

    print(
        f"Erros HTTP: "
        f"{stats['erros']}"
    )

    print(
        f"Reforço encontrado: "
        f"{resumo['reforco_encontrado']}"
    )

    print(
        f"Anulação encontrada: "
        f"{resumo['anulacao_encontrada']}"
    )

    print(
        f"cod_item encontrado: "
        f"{resumo['cod_item_encontrado']}"
    )

    print(
        f"Indicadores de restos: "
        f"{resumo['indicadores_restos']}"
    )

    print(
        f"Fórmula correta com movimentação: "
        f"{resumo['formula_ok_com_movimentacao']}"
    )

    print()
    print(
        f"CSV: {CSV_SAIDA}"
    )

    print(
        f"JSON: {JSON_SAIDA}"
    )

    print(
        f"Checkpoint: {CHECKPOINT}"
    )

    print("=" * 75)


if __name__ == "__main__":

    main()