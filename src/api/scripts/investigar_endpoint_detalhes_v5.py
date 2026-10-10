"""
investigar_endpoint_detalhes_v5.py

Objetivo
--------
Investigar o HTML REAL da página /Despesas procurando:

    - JavaScript inline
    - chamadas AJAX
    - fetch
    - endpoints /Despesas/*
    - detalhes de empenho
    - movimentações
    - reforço
    - anulação

A V5 NÃO faz:
    - varredura de favorecidos
    - consulta de milhares de registros
    - brute force de endpoints

Ela analisa somente a página e faz poucas requisições
pontuais aos endpoints explicitamente encontrados.

"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_URL = "https://www.transparencia.sp.gov.br"

DESPESAS_URL = f"{BASE_URL}/Despesas"

OUTPUT_DIR = Path("data/output")

HTML_FILE = OUTPUT_DIR / "investigacao_endpoint_v4_html.html"

RESULTADO_FILE = (
    OUTPUT_DIR / "investigacao_endpoint_detalhes_v5.json"
)

CONTEXTO_FILE = (
    OUTPUT_DIR / "investigacao_endpoint_detalhes_v5_contextos.txt"
)

TIMEOUT = 30


# ============================================================
# TERMOS DE INTERESSE
# ============================================================

TERMOS = [
    "/Despesas/",
    "Despesas/",
    "vl_reforco",
    "vl_anulacao",
    "vl_empenhado_inicial",
    "num_empenho",
    "numero_empenho",
    "empenho",
    "empenhos",
    "movimentacao",
    "movimentacoes",
    "movimento",
    "detalhe",
    "detalhes",
    "detalhamento",
    "reforco",
    "reforço",
    "anulacao",
    "anulação",
    "ajax",
    "$.ajax",
    "$.post",
    "$.get",
    "fetch(",
    "url:",
]


# ============================================================
# ENDPOINTS QUE JÁ SABEMOS QUE EXISTEM
# ============================================================

# Não são tratados como descoberta nova.
# Servem apenas como referência para comparar
# o que aparece no HTML.

ENDPOINTS_CONHECIDOS = [
    "/Despesas/Combos",
    "/Despesas/Filtro",
    "/Despesas/Buscar",
    "/Despesas/ExportarCsv",
    "/Despesas/ExportarPdf",
]


# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/154.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Referer": BASE_URL,
    }
)


# ============================================================
# ESTATÍSTICAS
# ============================================================

stats = {
    "inicio": datetime.now().isoformat(),
    "requisicoes": 0,
    "erros": 0,
    "termos_encontrados": {},
    "scripts_inline": 0,
    "endpoints_novos": 0,
    "endpoints_conhecidos": 0,
    "endpoints_testados": 0,
}


# ============================================================
# GET
# ============================================================

def get(
    url: str,
) -> requests.Response | None:

    stats["requisicoes"] += 1

    try:

        response = session.get(
            url,
            timeout=TIMEOUT,
        )

        if response.status_code != 200:

            stats["erros"] += 1

            print(
                f"❌ HTTP {response.status_code}: {url}"
            )

            return None

        return response

    except requests.RequestException as exc:

        stats["erros"] += 1

        print(
            f"❌ Erro: {exc}"
        )

        return None


# ============================================================
# 1. CARREGAR HTML
# ============================================================

def carregar_html() -> str | None:

    print()
    print("=" * 80)
    print("🌐 ETAPA 1 — CARREGANDO HTML")
    print("=" * 80)

    # Primeiro tenta usar o HTML já baixado pela V4.
    if HTML_FILE.exists():

        print()
        print(
            "✅ Utilizando HTML já salvo pela V4:"
        )

        print(
            f"   {HTML_FILE}"
        )

        return HTML_FILE.read_text(
            encoding="utf-8",
            errors="ignore",
        )

    # Caso não exista, baixa novamente.

    print()
    print(
        f"→ {DESPESAS_URL}"
    )

    response = get(
        DESPESAS_URL
    )

    if response is None:

        return None

    html = response.text

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    HTML_FILE.write_text(
        html,
        encoding="utf-8",
    )

    print(
        f"✅ HTML: {len(html):,} caracteres"
    )

    return html


# ============================================================
# 2. EXTRAIR SCRIPTS INLINE
# ============================================================

def extrair_scripts_inline(
    html: str,
) -> list[str]:

    print()
    print("=" * 80)
    print("📜 ETAPA 2 — SCRIPTS INLINE")
    print("=" * 80)

    padrao = re.compile(
        r"<script\b([^>]*)>(.*?)</script>",
        re.IGNORECASE | re.DOTALL,
    )

    scripts = []

    for match in padrao.finditer(html):

        atributos = match.group(1)

        conteudo = match.group(2)

        # Script externo.
        if re.search(
            r"\bsrc\s*=",
            atributos,
            re.IGNORECASE,
        ):

            continue

        if not conteudo.strip():

            continue

        scripts.append(
            conteudo
        )

    stats[
        "scripts_inline"
    ] = len(scripts)

    print()
    print(
        f"Scripts inline encontrados: "
        f"{len(scripts)}"
    )

    for index, script in enumerate(
        scripts,
        start=1,
    ):

        print(
            f"   {index:02d}. "
            f"{len(script):,} caracteres"
        )

    return scripts


# ============================================================
# 3. PROCURAR TERMOS
# ============================================================

def procurar_termos(
    texto: str,
) -> dict[str, list[int]]:

    resultado = {}

    texto_lower = texto.lower()

    for termo in TERMOS:

        termo_lower = termo.lower()

        posicoes = []

        inicio = 0

        while True:

            posicao = texto_lower.find(
                termo_lower,
                inicio,
            )

            if posicao == -1:

                break

            posicoes.append(
                posicao
            )

            inicio = (
                posicao
                + len(termo_lower)
            )

        if posicoes:

            resultado[
                termo
            ] = posicoes

    return resultado


# ============================================================
# 4. CONTEXTO
# ============================================================

def contexto(
    texto: str,
    posicao: int,
    antes: int = 1000,
    depois: int = 1800,
) -> str:

    inicio = max(
        0,
        posicao - antes,
    )

    fim = min(
        len(texto),
        posicao + depois,
    )

    return texto[
        inicio:fim
    ]


# ============================================================
# 5. EXTRAIR ENDPOINTS
# ============================================================

def extrair_endpoints(
    texto: str,
) -> list[str]:

    endpoints = set()

    # --------------------------------------------------------
    # URLs absolutas
    # --------------------------------------------------------

    padrao_absoluto = re.compile(
        r'https?://[^"\'\s<>]+',
        re.IGNORECASE,
    )

    for match in padrao_absoluto.finditer(
        texto
    ):

        url = match.group(0)

        if (
            "transparencia.sp.gov.br"
            in url.lower()
        ):

            url = url.rstrip(
                ".,;)"
            )

            endpoints.add(
                url
            )

    # --------------------------------------------------------
    # URLs relativas
    # --------------------------------------------------------

    padrao_relativo = re.compile(
        r'["\'](/[^"\']+)["\']',
        re.IGNORECASE,
    )

    for match in padrao_relativo.finditer(
        texto
    ):

        caminho = match.group(1)

        if (
            "/despesas/"
            not in caminho.lower()
        ):

            continue

        # Remover possíveis parâmetros
        # excessivamente grandes.

        if len(caminho) > 500:

            continue

        endpoints.add(
            urljoin(
                BASE_URL,
                caminho,
            )
        )

    # --------------------------------------------------------
    # Strings sem barra inicial
    # --------------------------------------------------------

    padrao_despesas = re.compile(
        r'["\'](Despesas/[^"\']+)["\']',
        re.IGNORECASE,
    )

    for match in padrao_despesas.finditer(
        texto
    ):

        caminho = "/" + match.group(1)

        endpoints.add(
            urljoin(
                BASE_URL,
                caminho,
            )
        )

    return sorted(
        endpoints
    )


# ============================================================
# 6. ANALISAR TODOS OS SCRIPTS
# ============================================================

def analisar_scripts(
    scripts: list[str],
) -> tuple[list[dict], list[str]]:

    print()
    print("=" * 80)
    print("🔎 ETAPA 3 — ANALISANDO SCRIPTS INLINE")
    print("=" * 80)

    analises = []

    todos_endpoints = set()

    for index, script in enumerate(
        scripts,
        start=1,
    ):

        encontrados = procurar_termos(
            script
        )

        endpoints = extrair_endpoints(
            script
        )

        if not encontrados and not endpoints:

            continue

        print()
        print(
            f"🎯 SCRIPT INLINE #{index}"
        )

        print(
            f"Tamanho: {len(script):,}"
        )

        print()

        if encontrados:

            print(
                "Termos encontrados:"
            )

            for termo, posicoes in (
                encontrados.items()
            ):

                print(
                    f"   {termo}: "
                    f"{len(posicoes)} ocorrência(s)"
                )

                stats[
                    "termos_encontrados"
                ][termo] = (
                    stats[
                        "termos_encontrados"
                    ].get(
                        termo,
                        0,
                    )
                    + len(posicoes)
                )

        if endpoints:

            print()
            print(
                "Endpoints encontrados:"
            )

            for endpoint in endpoints:

                print(
                    f"   → {endpoint}"
                )

                todos_endpoints.add(
                    endpoint
                )

        analises.append(
            {
                "indice": index,
                "tamanho": len(script),
                "termos": {
                    termo: posicoes
                    for termo, posicoes
                    in encontrados.items()
                },
                "endpoints": endpoints,
            }
        )

    return (
        analises,
        sorted(
            todos_endpoints
        ),
    )


# ============================================================
# 7. IMPRIMIR CONTEXTOS IMPORTANTES
# ============================================================

def imprimir_contextos(
    scripts: list[str],
):

    print()
    print("=" * 80)
    print("🧩 ETAPA 4 — CONTEXTOS DE AJAX / EMPENHO")
    print("=" * 80)

    termos_contexto = [
        "/Despesas/",
        "$.ajax",
        "$.post",
        "$.get",
        "fetch(",
        "vl_reforco",
        "vl_anulacao",
        "num_empenho",
        "detalhamento",
        "movimentacao",
        "reforco",
        "anulacao",
    ]

    saida = []

    for index, script in enumerate(
        scripts,
        start=1,
    ):

        encontrados = procurar_termos(
            script
        )

        for termo in termos_contexto:

            posicoes = encontrados.get(
                termo,
                [],
            )

            # Mostrar no máximo 5 contextos
            # de cada termo.

            for posicao in posicoes[:5]:

                trecho = contexto(
                    script,
                    posicao,
                )

                bloco = (
                    "\n"
                    + "=" * 100
                    + "\n"
                    + f"SCRIPT INLINE #{index}\n"
                    + f"TERMO: {termo}\n"
                    + "=" * 100
                    + "\n"
                    + trecho
                    + "\n"
                )

                saida.append(
                    bloco
                )

                print(
                    bloco
                )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    CONTEXTO_FILE.write_text(
        "\n".join(saida),
        encoding="utf-8",
    )

    print()
    print(
        f"💾 Contextos salvos em:"
    )

    print(
        f"   {CONTEXTO_FILE}"
    )


# ============================================================
# 8. CLASSIFICAR ENDPOINTS
# ============================================================

def classificar_endpoint(
    endpoint: str,
) -> dict:

    endpoint_lower = endpoint.lower()

    if endpoint_lower in [
        urljoin(
            BASE_URL,
            item,
        ).lower()
        for item in ENDPOINTS_CONHECIDOS
    ]:

        tipo = "CONHECIDO"

        stats[
            "endpoints_conhecidos"
        ] += 1

    else:

        tipo = "NOVO"

        stats[
            "endpoints_novos"
        ] += 1

    motivos = []

    palavras = [
        "empenho",
        "moviment",
        "detalh",
        "refor",
        "anul",
        "despesas",
    ]

    for palavra in palavras:

        if palavra in endpoint_lower:

            motivos.append(
                palavra
            )

    return {
        "url": endpoint,
        "tipo": tipo,
        "motivos": motivos,
    }


# ============================================================
# 9. TESTAR SOMENTE ENDPOINTS NOVOS
# ============================================================

def testar_endpoints(
    endpoints: list[str],
) -> list[dict]:

    print()
    print("=" * 80)
    print("🧪 ETAPA 5 — TESTANDO ENDPOINTS NOVOS")
    print("=" * 80)

    resultados = []

    classificados = [
        classificar_endpoint(
            endpoint
        )
        for endpoint in endpoints
    ]

    # Somente endpoints NOVOS.
    novos = [
        item
        for item in classificados
        if item["tipo"] == "NOVO"
    ]

    print()
    print(
        f"Endpoints novos: {len(novos)}"
    )

    # Limite de segurança.
    # Não queremos brute force.

    novos = novos[:10]

    for item in novos:

        url = item["url"]

        print()
        print(
            f"→ {url}"
        )

        stats[
            "requisicoes"
        ] += 1

        stats[
            "endpoints_testados"
        ] = (
            stats[
                "endpoints_testados"
            ]
            + 1
        )

        try:

            response = session.get(
                url,
                headers={
                    "Accept": (
                        "application/json,"
                        "text/plain,*/*"
                    ),
                    "X-Requested-With":
                        "XMLHttpRequest",
                    "Referer":
                        DESPESAS_URL,
                },
                timeout=TIMEOUT,
            )

            resultado = {
                "url": url,
                "status": response.status_code,
                "content_type":
                    response.headers.get(
                        "Content-Type"
                    ),
                "tamanho":
                    len(response.content),
            }

            print(
                f"   HTTP: "
                f"{response.status_code}"
            )

            print(
                f"   Content-Type: "
                f"{resultado['content_type']}"
            )

            print(
                f"   Tamanho: "
                f"{resultado['tamanho']:,}"
            )

            if response.status_code == 200:

                texto = response.text

                resultado[
                    "inicio_resposta"
                ] = texto[:3000]

                try:

                    resultado[
                        "json"
                    ] = response.json()

                except ValueError:

                    resultado[
                        "json"
                    ] = None

            resultados.append(
                resultado
            )

        except requests.RequestException as exc:

            stats[
                "erros"
            ] += 1

            resultados.append(
                {
                    "url": url,
                    "erro": str(exc),
                }
            )

    return resultados


# ============================================================
# 10. MAIN
# ============================================================

def main():

    inicio = time.time()

    print()
    print("=" * 80)
    print("🔬 INVESTIGAÇÃO DE ENDPOINTS — V5")
    print("=" * 80)

    print()
    print(
        "Objetivo: encontrar a chamada REAL "
        "usada pela página /Despesas."
    )

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    html = carregar_html()

    if not html:

        print(
            "\n❌ Não foi possível carregar o HTML."
        )

        return

    # --------------------------------------------------------
    # SCRIPTS INLINE
    # --------------------------------------------------------

    scripts = extrair_scripts_inline(
        html
    )

    # --------------------------------------------------------
    # ANALISAR
    # --------------------------------------------------------

    analises, endpoints = analisar_scripts(
        scripts
    )

    # --------------------------------------------------------
    # CONTEXTOS
    # --------------------------------------------------------

    imprimir_contextos(
        scripts
    )

    # --------------------------------------------------------
    # TESTAR
    # --------------------------------------------------------

    resultados = testar_endpoints(
        endpoints
    )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    stats[
        "tempo_segundos"
    ] = round(
        time.time() - inicio,
        2,
    )

    stats[
        "fim"
    ] = datetime.now().isoformat()

    resultado_final = {
        "estatisticas": stats,
        "endpoints_encontrados": [
            classificar_endpoint(
                endpoint
            )
            for endpoint in endpoints
        ],
        "resultados": resultados,
        "analises_scripts": analises,
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULTADO_FILE.write_text(
        json.dumps(
            resultado_final,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # RESUMO
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("🏁 V5 FINALIZADA")
    print("=" * 80)

    print()
    print(
        f"Scripts inline: "
        f"{stats['scripts_inline']}"
    )

    print(
        f"Endpoints encontrados: "
        f"{len(endpoints)}"
    )

    print(
        f"Endpoints novos: "
        f"{stats['endpoints_novos']}"
    )

    print(
        f"Endpoints conhecidos: "
        f"{stats['endpoints_conhecidos']}"
    )

    print(
        f"Endpoints testados: "
        f"{stats['endpoints_testados']}"
    )

    print(
        f"Requisições HTTP: "
        f"{stats['requisicoes']}"
    )

    print(
        f"Erros: "
        f"{stats['erros']}"
    )

    print()
    print(
        "Arquivos:"
    )

    print(
        f"   Resultado: {RESULTADO_FILE}"
    )

    print(
        f"   Contextos: {CONTEXTO_FILE}"
    )


if __name__ == "__main__":
    main()
