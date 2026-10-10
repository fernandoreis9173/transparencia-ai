"""
investigar_movimentacoes_v3.py

Objetivo
--------
Descobrir exclusivamente onde o Portal da Transparência de SP
disponibiliza informações de:

    - Reforço de Empenho
    - Anulação de Empenho

A V3 NÃO faz uma varredura completa dos favorecidos.

Estratégia:
    1. Testar diferentes valores de tipoRetorno.
    2. Testar diferentes combinações de filtros.
    3. Consultar favorecidos já conhecidos por possuírem múltiplos empenhos.
    4. Consultar empenhos que apresentam comportamento anômalo:
           vl_liquidado > vl_empenhado
    5. Procurar campos de movimentação conhecidos e possíveis
       nomenclaturas alternativas.
    6. Registrar a resposta original para posterior investigação.

IMPORTANTE:
    - Os valores retornados pela API nunca são alterados.
    - Não assumir que reforço/anulação inexistentes no sample
      significam que o Portal não disponibiliza esses dados.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_URL = "https://www.transparencia.sp.gov.br"

ENDPOINT = f"{BASE_URL}/Despesas/Buscar"

ANO = 2025

PAGE_SIZE = 50

TIMEOUT = 60

OUTPUT_DIR = Path("data/output")

CSV_OUTPUT = OUTPUT_DIR / "investigacao_movimentacoes_v3.csv"

JSON_OUTPUT = OUTPUT_DIR / "investigacao_movimentacoes_v3_resumo.json"

RAW_OUTPUT = OUTPUT_DIR / "investigacao_movimentacoes_v3_raw.json"


# ============================================================
# FAVORECIDOS JÁ CONHECIDOS
# ============================================================

# Favorecidos que já apresentaram múltiplos empenhos
# nas investigações anteriores.

FAVORECIDOS_MULTIPLOS = [
    "32691514000127",
    "24921239000162",
    "60629992000142",
    "26875439000151",
    "26800124000145",
    "44065663000160",
    "26226412000138",
    "23390187000182",
    "27278790000128",
    "23444446000100",
]


# ============================================================
# CAMPOS DE MOVIMENTAÇÃO
# ============================================================

CAMPOS_REFORCO = [
    "vl_reforco",
    "valor_reforco",
    "reforco",
    "vl_reforço",
    "valor_reforço",
]

CAMPOS_ANULACAO = [
    "vl_anulacao",
    "valor_anulacao",
    "anulacao",
    "vl_anulação",
    "valor_anulação",
]

# Campos relacionados que também serão procurados.
CAMPOS_MOVIMENTACAO = [
    "vl_empenhado",
    "vl_empenhado_inicial",
    "vl_reforco",
    "vl_anulacao",
    "vl_liquidado",
    "vl_pago",
    "vl_pago_rp",
]


# ============================================================
# POSSÍVEIS TIPOS DE RETORNO
# ============================================================

# A ideia é descobrir se o endpoint aceita alguma granularidade
# diferente daquelas já conhecidas.

TIPOS_RETORNO_TESTAR = [
    "empenho",
    "empenhos",
    "movimentacao",
    "movimentacoes",
    "despesa",
    "despesas",
    "favorecido",
    "orgao",
    "funcao",
    "programa",
]


# ============================================================
# SESSÃO HTTP
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/154.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/Despesas",
    }
)


# ============================================================
# ESTATÍSTICAS
# ============================================================

stats = {
    "inicio": datetime.now().isoformat(),
    "requisicoes": 0,
    "erros": 0,
    "sucessos": 0,
    "tipos_aceitos": [],
    "tipos_com_itens": [],
    "reforco_encontrado": 0,
    "anulacao_encontrada": 0,
    "registros_com_movimentacao": 0,
    "registros_liquidado_maior_empenhado": 0,
}


raw_responses = []


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def valor_numerico(valor: Any) -> float:
    """
    Converte valores numéricos para float de maneira segura.
    """
    if valor is None:
        return 0.0

    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def procurar_chaves(obj: Any, chaves: list[str]) -> dict[str, Any]:
    """
    Procura recursivamente chaves relacionadas a movimentações
    dentro de um JSON.

    Isso é importante porque a API pode eventualmente colocar
    os dados dentro de objetos aninhados.
    """

    encontradas = {}

    if isinstance(obj, dict):

        for chave, valor in obj.items():

            chave_lower = str(chave).lower()

            for alvo in chaves:

                if chave_lower == alvo.lower():

                    encontradas[chave] = valor

            encontradas.update(
                procurar_chaves(valor, chaves)
            )

    elif isinstance(obj, list):

        for item in obj:

            encontradas.update(
                procurar_chaves(item, chaves)
            )

    return encontradas


def procurar_chaves_movimentacao(obj: Any) -> dict[str, Any]:
    """
    Procura possíveis campos relacionados a reforço/anulação.
    """

    todas = (
        CAMPOS_REFORCO
        + CAMPOS_ANULACAO
        + CAMPOS_MOVIMENTACAO
    )

    return procurar_chaves(obj, todas)


def detectar_movimentacao(item: dict[str, Any]) -> dict[str, Any]:
    """
    Analisa um registro individual.
    """

    reforco = 0.0
    anulacao = 0.0

    campos_retorno = {}

    # --------------------------------------------------------
    # Reforço
    # --------------------------------------------------------

    for campo in CAMPOS_REFORCO:

        if campo in item:

            valor = valor_numerico(item[campo])

            campos_retorno[campo] = item[campo]

            if valor != 0:
                reforco += valor

    # --------------------------------------------------------
    # Anulação
    # --------------------------------------------------------

    for campo in CAMPOS_ANULACAO:

        if campo in item:

            valor = valor_numerico(item[campo])

            campos_retorno[campo] = item[campo]

            if valor != 0:
                anulacao += valor

    empenhado = valor_numerico(
        item.get("vl_empenhado")
    )

    liquidado = valor_numerico(
        item.get("vl_liquidado")
    )

    resultado = {
        "reforco": reforco,
        "anulacao": anulacao,
        "tem_reforco": reforco != 0,
        "tem_anulacao": anulacao != 0,
        "liquidado_maior_empenhado": (
            liquidado > empenhado
        ),
        "campos_movimentacao": campos_retorno,
    }

    return resultado


def montar_payload(
    tipo_retorno: str,
    page: int = 1,
    favorecido: str | None = None,
    cod_orgao: int | None = None,
    cod_funcao: int | None = None,
    codigo_filtro: str | None = None,
) -> dict[str, Any]:

    return {
        "tipoRetorno": tipo_retorno,
        "anoExercicio": ANO,

        "dataInicio": None,
        "dataTermino": None,

        "codigoFiltro": codigo_filtro,

        "nomeFavorecido": None,
        "cpfCnpjFavorecido": favorecido,

        "codOrgao": cod_orgao,
        "codFuncao": cod_funcao,
        "codSubfuncao": None,
        "codPrograma": None,
        "codAcao": None,
        "codElemento": None,

        "page": page,
        "pageSize": PAGE_SIZE,
        "totalItens": 0,
    }


def consultar(payload: dict[str, Any]) -> dict[str, Any] | None:

    stats["requisicoes"] += 1

    try:

        response = session.post(
            ENDPOINT,
            json=payload,
            timeout=TIMEOUT,
        )

        if response.status_code != 200:

            stats["erros"] += 1

            print(
                f"   ❌ HTTP {response.status_code}"
            )

            return None

        stats["sucessos"] += 1

        try:
            return response.json()

        except json.JSONDecodeError:

            print("   ⚠️ Resposta não é JSON")

            stats["erros"] += 1

            return None

    except requests.RequestException as exc:

        stats["erros"] += 1

        print(
            f"   ❌ Erro HTTP: {exc}"
        )

        return None


# ============================================================
# TESTE 1
# DESCOBRIR TIPOS DE RETORNO ACEITOS
# ============================================================

def investigar_tipos_retorno():

    print()
    print("=" * 80)
    print("🔎 TESTE 1 — TIPOS DE RETORNO")
    print("=" * 80)

    resultados = []

    for tipo in TIPOS_RETORNO_TESTAR:

        print(
            f"\n→ Testando tipoRetorno='{tipo}'"
        )

        payload = montar_payload(
            tipo_retorno=tipo
        )

        inicio = time.time()

        resposta = consultar(payload)

        tempo = time.time() - inicio

        resultado = {
            "tipoRetorno": tipo,
            "tempo": round(tempo, 3),
            "aceito": resposta is not None,
            "totalItems": None,
            "chaves": [],
        }

        if resposta is not None:

            resultado["chaves"] = list(
                resposta.keys()
            )

            resultado["totalItems"] = resposta.get(
                "totalItems"
            )

            itens = resposta.get(
                "items",
                []
            )

            if itens:

                stats["tipos_com_itens"].append(
                    tipo
                )

                chaves_mov = (
                    procurar_chaves_movimentacao(
                        itens
                    )
                )

                if chaves_mov:

                    print(
                        "   🚨 CAMPOS DE MOVIMENTAÇÃO "
                        "ENCONTRADOS:"
                    )

                    for chave, valor in chaves_mov.items():

                        print(
                            f"      {chave}: {valor}"
                        )

            stats["tipos_aceitos"].append(tipo)

        resultados.append(resultado)

        print(
            f"   Aceito: {resultado['aceito']}"
        )

        print(
            f"   Total: {resultado['totalItems']}"
        )

    return resultados


# ============================================================
# TESTE 2
# CONSULTAR FAVORECIDOS MULTI-EMPENHO
# ============================================================

def investigar_favorecidos_multiplos():

    print()
    print("=" * 80)
    print("🔎 TESTE 2 — FAVORECIDOS COM MÚLTIPLOS EMPENHOS")
    print("=" * 80)

    resultados = []

    for cpf_cnpj in FAVORECIDOS_MULTIPLOS:

        print()
        print(
            f"→ Favorecido: {cpf_cnpj}"
        )

        payload = montar_payload(
            tipo_retorno="favorecido",
            favorecido=cpf_cnpj,
        )

        resposta = consultar(payload)

        if not resposta:

            continue

        itens = resposta.get(
            "items",
            []
        )

        print(
            f"   Empenhos encontrados: {len(itens)}"
        )

        for item in itens:

            diagnostico = detectar_movimentacao(
                item
            )

            registro = {
                "origem": "favorecido_multiplo",
                "cpf_cnpj": cpf_cnpj,
                "num_empenho": item.get(
                    "num_empenho"
                ),
                "diagnostico": diagnostico,
                "item": item,
            }

            resultados.append(
                registro
            )

            processar_diagnostico(
                registro
            )

    return resultados


# ============================================================
# TESTE 3
# EMPENHOS COM LIQUIDADO > EMPENHADO
# ============================================================

def investigar_anomalias():

    print()
    print("=" * 80)
    print("🔎 TESTE 3 — LIQUIDADO > EMPENHADO")
    print("=" * 80)

    resultados = []

    # Favorecidos conhecidos que já apresentaram
    # registros com essa característica.

    favorecidos = [
        "26875439000151",
        "20174368000183",
        "60629992000142",
    ]

    for cpf_cnpj in favorecidos:

        print(
            f"\n→ Consultando {cpf_cnpj}"
        )

        payload = montar_payload(
            tipo_retorno="favorecido",
            favorecido=cpf_cnpj,
        )

        resposta = consultar(payload)

        if not resposta:
            continue

        itens = resposta.get(
            "items",
            []
        )

        for item in itens:

            empenhado = valor_numerico(
                item.get("vl_empenhado")
            )

            liquidado = valor_numerico(
                item.get("vl_liquidado")
            )

            if liquidado > empenhado:

                print()
                print(
                    "   🚨 ANOMALIA ENCONTRADA"
                )

                print(
                    f"      Empenho: "
                    f"{item.get('num_empenho')}"
                )

                print(
                    f"      Empenhado: "
                    f"{empenhado:,.2f}"
                )

                print(
                    f"      Liquidado: "
                    f"{liquidado:,.2f}"
                )

                print(
                    "      Campos de movimentação:"
                )

                campos = (
                    procurar_chaves_movimentacao(
                        item
                    )
                )

                for chave, valor in campos.items():

                    print(
                        f"         {chave}: {valor}"
                    )

                diagnostico = detectar_movimentacao(
                    item
                )

                registro = {
                    "origem": "anomalia",
                    "cpf_cnpj": cpf_cnpj,
                    "num_empenho": item.get(
                        "num_empenho"
                    ),
                    "diagnostico": diagnostico,
                    "item": item,
                }

                resultados.append(
                    registro
                )

                processar_diagnostico(
                    registro
                )

    return resultados


# ============================================================
# TESTE 4
# TESTAR FILTROS DIRECIONADOS
# ============================================================

def investigar_filtros():

    print()
    print("=" * 80)
    print("🔎 TESTE 4 — FILTROS DIRECIONADOS")
    print("=" * 80)

    resultados = []

    testes = [

        {
            "nome": "orgao_48000",
            "tipo": "favorecido",
            "cod_orgao": 48000,
        },

        {
            "nome": "orgao_48000_funcao_12",
            "tipo": "favorecido",
            "cod_orgao": 48000,
            "cod_funcao": 12,
        },

        {
            "nome": "orgao_21000",
            "tipo": "favorecido",
            "cod_orgao": 21000,
        },

        {
            "nome": "orgao_20000",
            "tipo": "favorecido",
            "cod_orgao": 20000,
        },
    ]

    for teste in testes:

        print()
        print(
            f"→ {teste['nome']}"
        )

        payload = montar_payload(
            tipo_retorno=teste["tipo"],
            cod_orgao=teste.get(
                "cod_orgao"
            ),
            cod_funcao=teste.get(
                "cod_funcao"
            ),
        )

        resposta = consultar(
            payload
        )

        if not resposta:
            continue

        itens = resposta.get(
            "items",
            []
        )

        print(
            f"   Registros: {len(itens)}"
        )

        campos = (
            procurar_chaves_movimentacao(
                itens
            )
        )

        if campos:

            print(
                "   🚨 Campos encontrados:"
            )

            for chave, valor in campos.items():

                print(
                    f"      {chave}: {valor}"
                )

        resultados.append(
            {
                "teste": teste,
                "resposta": resposta,
                "campos_movimentacao": campos,
            }
        )

    return resultados


# ============================================================
# PROCESSAMENTO DO DIAGNÓSTICO
# ============================================================

def processar_diagnostico(
    registro: dict[str, Any]
):

    diagnostico = registro[
        "diagnostico"
    ]

    if diagnostico["tem_reforco"]:

        stats[
            "reforco_encontrado"
        ] += 1

        print(
            "      🔴 REFORÇO ENCONTRADO"
        )

    if diagnostico["tem_anulacao"]:

        stats[
            "anulacao_encontrada"
        ] += 1

        print(
            "      🔴 ANULAÇÃO ENCONTRADA"
        )

    if (
        diagnostico[
            "tem_reforco"
        ]
        or diagnostico[
            "tem_anulacao"
        ]
    ):

        stats[
            "registros_com_movimentacao"
        ] += 1

    if diagnostico[
        "liquidado_maior_empenhado"
    ]:

        stats[
            "registros_liquidado_maior_empenhado"
        ] += 1


# ============================================================
# SALVAR RESULTADOS
# ============================================================

def salvar_json(
    resultados: dict[str, Any]
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        JSON_OUTPUT,
        "w",
        encoding="utf-8",
    ) as arquivo:

        json.dump(
            resultados,
            arquivo,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


def salvar_raw(
    dados: list[Any]
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        RAW_OUTPUT,
        "w",
        encoding="utf-8",
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


# ============================================================
# EXECUÇÃO
# ============================================================

def main():

    print()
    print("=" * 80)
    print("🔬 INVESTIGAÇÃO DE MOVIMENTAÇÕES — V3")
    print("=" * 80)

    print()
    print(
        "Objetivo:"
    )

    print(
        "Descobrir onde o Portal disponibiliza "
        "REFORÇO e ANULAÇÃO de empenho."
    )

    print()
    print(
        f"Ano: {ANO}"
    )

    print(
        f"Endpoint: {ENDPOINT}"
    )

    inicio = time.time()

    resultados = {
        "tipos_retorno": [],
        "favorecidos_multiplos": [],
        "anomalias": [],
        "filtros": [],
    }

    # --------------------------------------------------------
    # 1. Descobrir tipos de retorno
    # --------------------------------------------------------

    resultados[
        "tipos_retorno"
    ] = investigar_tipos_retorno()

    # --------------------------------------------------------
    # 2. Favorecidos com múltiplos empenhos
    # --------------------------------------------------------

    resultados[
        "favorecidos_multiplos"
    ] = investigar_favorecidos_multiplos()

    # --------------------------------------------------------
    # 3. Anomalias conhecidas
    # --------------------------------------------------------

    resultados[
        "anomalias"
    ] = investigar_anomalias()

    # --------------------------------------------------------
    # 4. Filtros
    # --------------------------------------------------------

    resultados[
        "filtros"
    ] = investigar_filtros()

    # --------------------------------------------------------
    # Finalização
    # --------------------------------------------------------

    tempo_total = time.time() - inicio

    stats["fim"] = datetime.now().isoformat()

    stats[
        "tempo_segundos"
    ] = round(
        tempo_total,
        2
    )

    resultados[
        "estatisticas"
    ] = stats

    salvar_json(
        resultados
    )

    salvar_raw(
        resultados
    )

    print()
    print("=" * 80)
    print("🏁 INVESTIGAÇÃO V3 FINALIZADA")
    print("=" * 80)

    print()
    print(
        f"Requisições HTTP: "
        f"{stats['requisicoes']}"
    )

    print(
        f"Erros HTTP: "
        f"{stats['erros']}"
    )

    print(
        f"Tipos aceitos: "
        f"{stats['tipos_aceitos']}"
    )

    print(
        f"Tipos com itens: "
        f"{stats['tipos_com_itens']}"
    )

    print()
    print(
        f"🔴 Reforços encontrados: "
        f"{stats['reforco_encontrado']}"
    )

    print(
        f"🔴 Anulações encontradas: "
        f"{stats['anulacao_encontrada']}"
    )

    print(
        f"Registros com movimentação: "
        f"{stats['registros_com_movimentacao']}"
    )

    print(
        f"Liquidado > Empenhado: "
        f"{stats['registros_liquidado_maior_empenhado']}"
    )

    print()
    print(
        f"JSON: {JSON_OUTPUT}"
    )

    print(
        f"RAW: {RAW_OUTPUT}"
    )


if __name__ == "__main__":
    main()