"""
investigar_endpoint_detalhes_v4.py

Objetivo
--------
Descobrir se o Portal da Transparência de SP possui algum endpoint
específico para:

    - detalhe do empenho
    - movimentações do empenho
    - reforço
    - anulação
    - eventos do empenho

A V4 NÃO faz varredura de favorecidos.

Estratégia
----------
1. Baixar a página /Despesas.
2. Identificar scripts JavaScript carregados pela página.
3. Baixar os JS relevantes.
4. Procurar referências a:
       - empenho
       - num_empenho
       - vl_reforco
       - vl_anulacao
       - detalhe
       - movimentacao
       - reforco
       - anulacao
       - Buscar
       - Filtro
       - Exportar
5. Extrair possíveis URLs/endpoints encontrados no JS.
6. Testar somente endpoints candidatos.
7. Consultar alguns empenhos conhecidos para tentar descobrir
   parâmetros de detalhe.

IMPORTANTE
----------
- Não altera nenhum dado.
- Não percorre milhares de favorecidos.
- Não considera HTTP 200 como prova de que um endpoint existe.
- Guarda as respostas para análise posterior.
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

HTML_OUTPUT = OUTPUT_DIR / "investigacao_endpoint_v4_html.html"

JS_INDEX_OUTPUT = OUTPUT_DIR / "investigacao_endpoint_v4_js.json"

ENDPOINTS_OUTPUT = OUTPUT_DIR / "investigacao_endpoint_v4_endpoints.json"

RESULTADO_OUTPUT = OUTPUT_DIR / "investigacao_endpoint_v4_resultado.json"

TIMEOUT = 30


# ============================================================
# EMPENHOS CONHECIDOS
# ============================================================

# São utilizados somente para testes pontuais.
# NÃO existe qualquer loop sobre milhares de registros.

EMPENHOS_TESTE = [
    "2025NE00068",
    "2025NE40343",
    "2025NE02936",
    "2025NE38710",
    "2025NE30224",
]


# ============================================================
# TERMOS IMPORTANTES
# ============================================================

TERMOS_PRIORITARIOS = [
    "vl_reforco",
    "vl_anulacao",
    "vl_empenhado_inicial",
    "num_empenho",
    "empenho",
    "empenhos",
    "movimentacao",
    "movimentacoes",
    "movimento",
    "detalhe",
    "detalhes",
    "detalhamento",
    "reforco",
    "anulacao",
    "anulação",
    "buscar",
    "filtro",
    "exportarcsv",
    "exportarpdf",
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
    "scripts_encontrados": 0,
    "scripts_baixados": 0,
    "scripts_relevantes": 0,
    "endpoints_encontrados": 0,
    "endpoints_testados": 0,
}


# ============================================================
# REQUISIÇÃO
# ============================================================

def get_url(
    url: str,
    headers: dict | None = None,
) -> requests.Response | None:

    stats["requisicoes"] += 1

    try:

        response = session.get(
            url,
            headers=headers,
            timeout=TIMEOUT,
        )

        if response.status_code != 200:

            stats["erros"] += 1

            print(
                f"   ❌ HTTP {response.status_code}: {url}"
            )

            return None

        return response

    except requests.RequestException as exc:

        stats["erros"] += 1

        print(
            f"   ❌ Erro: {url}"
        )

        print(
            f"      {exc}"
        )

        return None


# ============================================================
# 1. BAIXAR HTML
# ============================================================

def baixar_html() -> str | None:

    print()
    print("=" * 80)
    print("🌐 ETAPA 1 — BAIXANDO PÁGINA /DESPESAS")
    print("=" * 80)

    print()
    print(
        f"URL: {DESPESAS_URL}"
    )

    response = get_url(
        DESPESAS_URL
    )

    if response is None:

        return None

    html = response.text

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    HTML_OUTPUT.write_text(
        html,
        encoding="utf-8",
    )

    print()
    print(
        f"✅ HTML recebido: "
        f"{len(html):,} caracteres"
    )

    print(
        f"💾 Salvo em: {HTML_OUTPUT}"
    )

    return html


# ============================================================
# 2. ENCONTRAR SCRIPTS
# ============================================================

def encontrar_scripts(
    html: str,
) -> list[str]:

    print()
    print("=" * 80)
    print("📜 ETAPA 2 — IDENTIFICANDO JAVASCRIPTS")
    print("=" * 80)

    encontrados = []

    # --------------------------------------------------------
    # <script src="...">
    # --------------------------------------------------------

    padrao_src = re.compile(
        r'<script[^>]+src=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )

    for match in padrao_src.finditer(html):

        src = match.group(1)

        url = urljoin(
            DESPESAS_URL,
            src,
        )

        if url not in encontrados:

            encontrados.append(url)

    # --------------------------------------------------------
    # Scripts inline também podem conter endpoints.
    # --------------------------------------------------------

    print()
    print(
        f"Scripts externos encontrados: "
        f"{len(encontrados)}"
    )

    for index, url in enumerate(
        encontrados,
        start=1,
    ):

        print(
            f"{index:02d}. {url}"
        )

    stats[
        "scripts_encontrados"
    ] = len(encontrados)

    return encontrados


# ============================================================
# 3. BAIXAR JS
# ============================================================

def baixar_scripts(
    scripts: list[str],
) -> list[dict]:

    print()
    print("=" * 80)
    print("📥 ETAPA 3 — BAIXANDO JAVASCRIPTS")
    print("=" * 80)

    resultados = []

    for index, url in enumerate(
        scripts,
        start=1,
    ):

        print()
        print(
            f"[{index}/{len(scripts)}]"
        )

        print(
            f"→ {url}"
        )

        response = get_url(
            url,
            headers={
                "Accept": (
                    "application/javascript,"
                    "text/javascript,"
                    "*/*"
                ),
                "Referer": DESPESAS_URL,
            },
        )

        if response is None:

            continue

        js = response.text

        resultados.append(
            {
                "url": url,
                "tamanho": len(js),
                "conteudo": js,
            }
        )

        stats[
            "scripts_baixados"
        ] += 1

        print(
            f"   ✅ {len(js):,} caracteres"
        )

    return resultados


# ============================================================
# 4. ANALISAR RELEVÂNCIA
# ============================================================

def encontrar_termos(
    texto: str,
) -> dict[str, int]:

    texto_lower = texto.lower()

    ocorrencias = {}

    for termo in TERMOS_PRIORITARIOS:

        quantidade = texto_lower.count(
            termo.lower()
        )

        if quantidade > 0:

            ocorrencias[termo] = quantidade

    return ocorrencias


# ============================================================
# 5. EXTRAIR CONTEXTO
# ============================================================

def extrair_contextos(
    texto: str,
    termo: str,
    limite: int = 10,
) -> list[str]:

    resultados = []

    texto_lower = texto.lower()

    termo_lower = termo.lower()

    inicio = 0

    while len(resultados) < limite:

        posicao = texto_lower.find(
            termo_lower,
            inicio,
        )

        if posicao == -1:

            break

        inicio_contexto = max(
            0,
            posicao - 500,
        )

        fim_contexto = min(
            len(texto),
            posicao + len(termo) + 1000,
        )

        contexto = texto[
            inicio_contexto:fim_contexto
        ]

        resultados.append(
            contexto
        )

        inicio = (
            posicao
            + len(termo)
        )

    return resultados


# ============================================================
# 6. EXTRAIR URLs
# ============================================================

def extrair_urls(
    texto: str,
) -> list[str]:

    urls = set()

    # URLs absolutas

    padrao_absoluto = re.compile(
        r'https?://[^\s"\'<>]+',
        re.IGNORECASE,
    )

    for match in padrao_absoluto.finditer(
        texto
    ):

        url = match.group(0)

        url = url.rstrip(
            ".,;)"
        )

        urls.add(url)

    # URLs relativas iniciadas com /

    padrao_relativo = re.compile(
        r'["\'](/[^"\']{1,300})["\']',
        re.IGNORECASE,
    )

    for match in padrao_relativo.finditer(
        texto
    ):

        caminho = match.group(1)

        # Evitar arquivos estáticos
        if caminho.lower().endswith(
            (
                ".js",
                ".css",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".svg",
                ".woff",
                ".woff2",
            )
        ):

            continue

        urls.add(
            urljoin(
                BASE_URL,
                caminho,
            )
        )

    return sorted(
        urls
    )


# ============================================================
# 7. ANALISAR SCRIPTS
# ============================================================

def analisar_scripts(
    scripts: list[dict],
) -> list[dict]:

    print()
    print("=" * 80)
    print("🔎 ETAPA 4 — ANALISANDO JAVASCRIPT")
    print("=" * 80)

    resultados = []

    for script in scripts:

        url = script["url"]

        js = script["conteudo"]

        ocorrencias = encontrar_termos(
            js
        )

        if not ocorrencias:

            continue

        stats[
            "scripts_relevantes"
        ] += 1

        print()
        print(
            "🎯 SCRIPT RELEVANTE"
        )

        print(
            f"URL: {url}"
        )

        print(
            "Termos encontrados:"
        )

        for termo, quantidade in (
            ocorrencias.items()
        ):

            print(
                f"   {termo}: {quantidade}"
            )

        urls = extrair_urls(
            js
        )

        print()
        print(
            f"URLs encontradas no JS: "
            f"{len(urls)}"
        )

        resultados.append(
            {
                "url": url,
                "tamanho": len(js),
                "termos": ocorrencias,
                "urls": urls,
                "contextos": {
                    termo: extrair_contextos(
                        js,
                        termo,
                    )
                    for termo in ocorrencias
                },
            }
        )

    return resultados


# ============================================================
# 8. EXTRAIR POSSÍVEIS ENDPOINTS
# ============================================================

def extrair_endpoints(
    analises: list[dict],
) -> list[dict]:

    print()
    print("=" * 80)
    print("🔗 ETAPA 5 — IDENTIFICANDO POSSÍVEIS ENDPOINTS")
    print("=" * 80)

    endpoints = {}

    palavras_endpoint = [
        "despesas",
        "empenho",
        "empenhos",
        "moviment",
        "detalh",
        "refor",
        "anul",
        "buscar",
        "filtro",
        "exportar",
    ]

    for analise in analises:

        origem = analise["url"]

        for url in analise["urls"]:

            url_lower = url.lower()

            score = 0

            motivos = []

            for palavra in palavras_endpoint:

                if palavra in url_lower:

                    score += 1

                    motivos.append(
                        palavra
                    )

            if score == 0:

                continue

            if url not in endpoints:

                endpoints[url] = {
                    "url": url,
                    "score": score,
                    "motivos": motivos,
                    "origens": [
                        origem
                    ],
                }

            else:

                endpoints[url][
                    "origens"
                ].append(
                    origem
                )

    lista = sorted(
        endpoints.values(),
        key=lambda x: (
            -x["score"],
            x["url"],
        ),
    )

    stats[
        "endpoints_encontrados"
    ] = len(lista)

    print()

    if not lista:

        print(
            "⚠️ Nenhum endpoint candidato encontrado."
        )

    else:

        for index, endpoint in enumerate(
            lista,
            start=1,
        ):

            print(
                f"{index:02d}. "
                f"[score={endpoint['score']}] "
                f"{endpoint['url']}"
            )

            print(
                f"    Motivos: "
                f"{', '.join(endpoint['motivos'])}"
            )

    return lista


# ============================================================
# 9. TESTAR ENDPOINTS
# ============================================================

def testar_endpoint(
    endpoint: dict,
) -> dict:

    url = endpoint["url"]

    print()
    print(
        "------------------------------------------------------------"
    )

    print(
        f"🔬 Testando: {url}"
    )

    resultado = {
        "url": url,
        "status": None,
        "content_type": None,
        "tamanho": None,
        "sucesso_http": False,
        "json": None,
        "texto_inicio": None,
        "campos_movimentacao": [],
    }

    stats[
        "endpoints_testados"
    ] += 1

    try:

        response = session.get(
            url,
            headers={
                "Accept": (
                    "application/json,"
                    "text/plain,*/*"
                ),
                "Referer": DESPESAS_URL,
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=TIMEOUT,
        )

        resultado["status"] = (
            response.status_code
        )

        resultado["content_type"] = (
            response.headers.get(
                "Content-Type"
            )
        )

        resultado["tamanho"] = len(
            response.content
        )

        resultado["sucesso_http"] = (
            response.status_code == 200
        )

        print(
            f"HTTP: {response.status_code}"
        )

        print(
            f"Content-Type: "
            f"{resultado['content_type']}"
        )

        print(
            f"Tamanho: "
            f"{resultado['tamanho']:,}"
        )

        if not resultado[
            "sucesso_http"
        ]:

            return resultado

        texto = response.text

        resultado[
            "texto_inicio"
        ] = texto[:2000]

        try:

            dados = response.json()

            resultado[
                "json"
            ] = dados

            campos = encontrar_campos_recursivos(
                dados
            )

            resultado[
                "campos_movimentacao"
            ] = campos

            if campos:

                print()
                print(
                    "🚨 CAMPOS IMPORTANTES ENCONTRADOS:"
                )

                for campo in campos:

                    print(
                        f"   → {campo}"
                    )

        except ValueError:

            print(
                "Resposta não é JSON."
            )

            texto_lower = texto.lower()

            encontrados = []

            for termo in TERMOS_PRIORITARIOS:

                if termo.lower() in texto_lower:

                    encontrados.append(
                        termo
                    )

            resultado[
                "campos_movimentacao"
            ] = encontrados

            if encontrados:

                print(
                    "Termos encontrados:"
                )

                for termo in encontrados:

                    print(
                        f"   → {termo}"
                    )

    except requests.RequestException as exc:

        resultado[
            "erro"
        ] = str(exc)

        print(
            f"❌ {exc}"
        )

    return resultado


# ============================================================
# 10. PROCURAR CAMPOS RECURSIVAMENTE
# ============================================================

def encontrar_campos_recursivos(
    obj,
) -> list[str]:

    encontrados = set()

    campos = {
        "vl_reforco",
        "vl_anulacao",
        "vl_empenhado",
        "vl_empenhado_inicial",
        "vl_liquidado",
        "vl_pago",
        "vl_pago_rp",
        "num_empenho",
        "numero_empenho",
        "empenho",
        "movimentacao",
        "movimento",
        "reforco",
        "anulacao",
    }

    def percorrer(valor):

        if isinstance(
            valor,
            dict,
        ):

            for chave, conteudo in valor.items():

                chave_lower = str(
                    chave
                ).lower()

                if chave_lower in campos:

                    encontrados.add(
                        chave
                    )

                percorrer(
                    conteudo
                )

        elif isinstance(
            valor,
            list,
        ):

            for item in valor:

                percorrer(
                    item
                )

    percorrer(
        obj
    )

    return sorted(
        encontrados
    )


# ============================================================
# 11. PROCURAR REFERÊNCIAS A EMPENHO NO JS
# ============================================================

def investigar_contextos_empenho(
    analises: list[dict],
):

    print()
    print("=" * 80)
    print("🧩 ETAPA 6 — CONTEXTOS DE EMPENHO")
    print("=" * 80)

    termos = [
        "num_empenho",
        "vl_reforco",
        "vl_anulacao",
        "detalhamento",
        "movimentacao",
    ]

    encontrados = []

    for analise in analises:

        for termo in termos:

            contextos = analise[
                "contextos"
            ].get(
                termo,
                []
            )

            for contexto in contextos:

                encontrados.append(
                    {
                        "script": analise["url"],
                        "termo": termo,
                        "contexto": contexto,
                    }
                )

                print()
                print(
                    f"🎯 TERMO: {termo}"
                )

                print(
                    f"SCRIPT: "
                    f"{analise['url']}"
                )

                print(
                    "-" * 70
                )

                # Não imprimir contexto gigantesco.
                print(
                    contexto[:1800]
                )

                print(
                    "-" * 70
                )

    return encontrados


# ============================================================
# 12. SALVAR RESULTADOS
# ============================================================

def salvar_json(
    caminho: Path,
    dados,
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        caminho,
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
# MAIN
# ============================================================

def main():

    inicio = time.time()

    print()
    print("=" * 80)
    print("🔬 INVESTIGAÇÃO DE ENDPOINTS — V4")
    print("=" * 80)

    print()
    print(
        "Esta investigação é cirúrgica."
    )

    print(
        "Nenhum processamento em massa de favorecidos será realizado."
    )

    # --------------------------------------------------------
    # ETAPA 1
    # --------------------------------------------------------

    html = baixar_html()

    if not html:

        print(
            "\n❌ Não foi possível obter a página."
        )

        return

    # --------------------------------------------------------
    # ETAPA 2
    # --------------------------------------------------------

    scripts = encontrar_scripts(
        html
    )

    # --------------------------------------------------------
    # ETAPA 3
    # --------------------------------------------------------

    scripts_baixados = baixar_scripts(
        scripts
    )

    # --------------------------------------------------------
    # ETAPA 4
    # --------------------------------------------------------

    analises = analisar_scripts(
        scripts_baixados
    )

    # --------------------------------------------------------
    # ETAPA 5
    # --------------------------------------------------------

    endpoints = extrair_endpoints(
        analises
    )

    # --------------------------------------------------------
    # ETAPA 6
    # --------------------------------------------------------

    contextos = investigar_contextos_empenho(
        analises
    )

    # --------------------------------------------------------
    # ETAPA 7
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("🧪 ETAPA 7 — TESTANDO ENDPOINTS CANDIDATOS")
    print("=" * 80)

    resultados_endpoints = []

    # Limite proposital.
    # A ideia NÃO é fazer uma varredura.
    #
    # Primeiro testar somente os 15 candidatos
    # mais relevantes.

    for endpoint in endpoints[:15]:

        resultado = testar_endpoint(
            endpoint
        )

        resultados_endpoints.append(
            resultado
        )

    # --------------------------------------------------------
    # SALVAR
    # --------------------------------------------------------

    tempo = time.time() - inicio

    stats[
        "tempo_segundos"
    ] = round(
        tempo,
        2,
    )

    stats[
        "fim"
    ] = datetime.now().isoformat()

    resultado_final = {
        "estatisticas": stats,
        "scripts": [
            {
                "url": item["url"],
                "tamanho": item["tamanho"],
            }
            for item in scripts_baixados
        ],
        "analises": analises,
        "endpoints": endpoints,
        "contextos_empenho": contextos,
        "resultados_endpoints": resultados_endpoints,
        "empenhos_teste": EMPENHOS_TESTE,
    }

    salvar_json(
        JS_INDEX_OUTPUT,
        resultado_final["scripts"],
    )

    salvar_json(
        ENDPOINTS_OUTPUT,
        endpoints,
    )

    salvar_json(
        RESULTADO_OUTPUT,
        resultado_final,
    )

    # --------------------------------------------------------
    # RESUMO
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("🏁 INVESTIGAÇÃO V4 FINALIZADA")
    print("=" * 80)

    print()
    print(
        f"Requisições HTTP: "
        f"{stats['requisicoes']}"
    )

    print(
        f"Erros: "
        f"{stats['erros']}"
    )

    print(
        f"Scripts encontrados: "
        f"{stats['scripts_encontrados']}"
    )

    print(
        f"Scripts baixados: "
        f"{stats['scripts_baixados']}"
    )

    print(
        f"Scripts relevantes: "
        f"{stats['scripts_relevantes']}"
    )

    print(
        f"Endpoints candidatos: "
        f"{stats['endpoints_encontrados']}"
    )

    print(
        f"Endpoints testados: "
        f"{stats['endpoints_testados']}"
    )

    print()
    print(
        f"HTML:"
        f" {HTML_OUTPUT}"
    )

    print(
        f"JS:"
        f" {JS_INDEX_OUTPUT}"
    )

    print(
        f"Endpoints:"
        f" {ENDPOINTS_OUTPUT}"
    )

    print(
        f"Resultado:"
        f" {RESULTADO_OUTPUT}"
    )


if __name__ == "__main__":
    main()
