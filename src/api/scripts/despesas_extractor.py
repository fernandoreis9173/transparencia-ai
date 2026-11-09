from __future__ import annotations

import math
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests


class ExtratorError(RuntimeError):
    """Erro base do extrator (mantém compatibilidade com RuntimeError)."""


class ErroHTTP(ExtratorError):
    """A API respondeu com um status HTTP de erro."""


class ErroRede(ExtratorError):
    """Falha de conexão, timeout ou outro erro de transporte."""


class ErroDecodificacao(ExtratorError):
    """O corpo da resposta não é um JSON válido."""


class RespostaInvalidaError(ExtratorError):
    """JSON válido, mas incompatível com o contrato esperado."""


class PaginacaoInconsistenteError(ExtratorError):
    """A paginação não é coerente com os totais informados pela API."""


class DuplicidadeConflitanteError(ExtratorError):
    """Mesma chave de empenho com conteúdos diferentes."""


# Chave que identifica um empenho. Se alguma coluna não existir na
# resposta, usa-se somente as colunas disponíveis, nesta ordem.
CHAVE_EMPENHO = ("ano_exercicio", "cod_uo", "num_empenho")

MAX_PAGINAS = 10_000


class DespesasExtractor:
    """
    Extrator reutilizável dos dados de despesas públicas
    do Portal da Transparência do Estado de São Paulo.

    Contrato esperado da API (validado em cada página):
      - ``items``: lista de registros;
      - ``totalItems``: inteiro >= 0;
      - ``totalPages`` e ``hasNext``: opcionais, mas, quando presentes,
        precisam ser coerentes com ``totalItems`` e ``pageSize``.
    """

    BASE_URL = "https://www.transparencia.sp.gov.br"
    ENDPOINT_BUSCAR = f"{BASE_URL}/Despesas/Buscar"

    def __init__(
        self,
        timeout: int = 60,
        max_retries: int = 3,
        delay: float = 0.2,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/154.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Transporte
    # ------------------------------------------------------------------

    @staticmethod
    def _repetir(status: int) -> bool:
        return status >= 500 or status in (408, 429)

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Executa uma requisição POST com retry e devolve o JSON (dict).

        Levanta ErroHTTP, ErroRede, ErroDecodificacao ou
        RespostaInvalidaError (JSON que não é um objeto).
        """

        ultimo_erro: ExtratorError | None = None

        for tentativa in range(1, self.max_retries + 1):
            repetir = True

            try:
                response = self.session.post(
                    self.ENDPOINT_BUSCAR,
                    json=payload,
                    timeout=self.timeout,
                )
            except requests.RequestException as erro:
                ultimo_erro = ErroRede(f"Erro de rede: {erro}")
                ultimo_erro.__cause__ = erro
            else:
                if response.status_code >= 400:
                    ultimo_erro = ErroHTTP(
                        f"HTTP {response.status_code} em "
                        f"{self.ENDPOINT_BUSCAR}"
                    )
                    repetir = self._repetir(response.status_code)
                else:
                    try:
                        corpo = response.json()
                    except ValueError as erro:
                        ultimo_erro = ErroDecodificacao(
                            f"Resposta não é um JSON válido: {erro}"
                        )
                        ultimo_erro.__cause__ = erro
                    else:
                        if not isinstance(corpo, dict):
                            raise RespostaInvalidaError(
                                "A resposta da API não é um objeto JSON "
                                f"(recebido: {type(corpo).__name__})."
                            )
                        return corpo

            print(
                f"Erro na requisição "
                f"(tentativa {tentativa}/{self.max_retries}): "
                f"{ultimo_erro}"
            )

            if not repetir:
                break

            if tentativa < self.max_retries:
                time.sleep(tentativa * 2)

        assert ultimo_erro is not None
        raise ultimo_erro

    def consultar(
        self,
        *,
        ano: int,
        tipo_retorno: str = "favorecido",
        page: int = 1,
        page_size: int = 50,
        data_inicio: str | None = None,
        data_termino: str | None = None,
        codigo_filtro: int | None = None,
        nome_favorecido: str | None = None,
        cpf_cnpj_favorecido: str | None = None,
        cod_orgao: int | None = None,
        cod_funcao: int | None = None,
        cod_subfuncao: int | None = None,
        cod_programa: int | None = None,
        cod_acao: int | None = None,
        cod_elemento: int | None = None,
    ) -> dict[str, Any]:

        payload = {
            "tipoRetorno": tipo_retorno,
            "anoExercicio": ano,
            "dataInicio": data_inicio,
            "dataTermino": data_termino,
            "codigoFiltro": codigo_filtro,
            "nomeFavorecido": nome_favorecido,
            "cpfCnpjFavorecido": cpf_cnpj_favorecido,
            "codOrgao": cod_orgao,
            "codFuncao": cod_funcao,
            "codSubfuncao": cod_subfuncao,
            "codPrograma": cod_programa,
            "codAcao": cod_acao,
            "codElemento": cod_elemento,
            "page": page,
            "pageSize": page_size,
            "totalItens": 0,
        }

        resultado = self._post(payload)

        time.sleep(self.delay)

        return resultado

    # ------------------------------------------------------------------
    # Validação do contrato
    # ------------------------------------------------------------------

    @staticmethod
    def _inteiro(valor: Any, campo: str, minimo: int = 0) -> int:
        if isinstance(valor, bool) or not isinstance(valor, int):
            if isinstance(valor, str) and valor.strip().isdigit():
                valor = int(valor.strip())
            else:
                raise RespostaInvalidaError(
                    f"Campo '{campo}' ausente ou inválido: {valor!r}."
                )

        if valor < minimo:
            raise RespostaInvalidaError(
                f"Campo '{campo}' fora do intervalo esperado: {valor!r}."
            )

        return valor

    @classmethod
    def _validar_pagina(
        cls,
        resultado: Any,
    ) -> tuple[list[dict[str, Any]], int, int | None, bool | None, int | None]:
        """
        Valida uma página e devolve
        (items, totalItems, totalPages, hasNext, pageSize).
        """

        if not isinstance(resultado, dict):
            raise RespostaInvalidaError(
                "A resposta da API não é um objeto JSON."
            )

        items = resultado.get("items")

        if not isinstance(items, list):
            raise RespostaInvalidaError(
                "Campo 'items' ausente ou não é uma lista. "
                f"Campos recebidos: {sorted(resultado)[:15]}."
            )

        if not all(isinstance(item, dict) for item in items):
            raise RespostaInvalidaError(
                "Campo 'items' contém elementos que não são objetos."
            )

        total_items = cls._inteiro(
            resultado.get("totalItems"), "totalItems"
        )

        total_pages = (
            cls._inteiro(resultado["totalPages"], "totalPages")
            if resultado.get("totalPages") is not None
            else None
        )

        has_next = resultado.get("hasNext")

        if has_next is not None and not isinstance(has_next, bool):
            raise RespostaInvalidaError(
                f"Campo 'hasNext' inválido: {has_next!r}."
            )

        page_size = (
            cls._inteiro(resultado["pageSize"], "pageSize", minimo=1)
            if resultado.get("pageSize") is not None
            else None
        )

        return items, total_items, total_pages, has_next, page_size

    @classmethod
    def _extrair_registros(
        cls,
        resultado: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Registros de uma página, já validada contra o contrato."""

        return cls._validar_pagina(resultado)[0]

    # ------------------------------------------------------------------
    # Paginação
    # ------------------------------------------------------------------

    
    def buscar_todas_paginas(
        self,
        *,
        ano: int,
        tipo_retorno: str,
        page_size: int = 50,
        chave_contagem: tuple[str, ...] | None = None,
        **filtros,
    ) -> list[dict[str, Any]]:
        """
        Busca todas as páginas.

        chave_contagem=None:
            totalItems representa a quantidade de linhas.

        chave_contagem=("num_empenho",):
            totalItems representa a quantidade de empenhos distintos.
            Todas as linhas retornadas são preservadas.
        """

        registros: list[dict[str, Any]] = []
        total_esperado: int | None = None
        pagina = 1
        chaves_encontradas: set[tuple] = set()

        def quantidade_validada() -> int:
            if chave_contagem is None:
                return len(registros)

            return len(chaves_encontradas)

        while True:
            if pagina > MAX_PAGINAS:
                raise PaginacaoInconsistenteError(
                    f"Limite de {MAX_PAGINAS} páginas excedido."
                )

            resposta = self.consultar(
                ano=ano,
                tipo_retorno=tipo_retorno,
                page=pagina,
                page_size=page_size,
                **filtros,
            )

            items, total, total_pages, has_next, size_resp = (
                self._validar_pagina(resposta)
            )
            
            chaves_pagina = {
                item.get("num_empenho")
                for item in items
                if item.get("num_empenho") is not None
            }
            
            print(
                "\nDIAGNÓSTICO DA API"
                f"\nPágina: {pagina}"
                f"\nLinhas recebidas: {len(items)}"
                f"\nEmpenhos distintos na página: {len(chaves_pagina)}"
                f"\ntotalItems: {total}"
                f"\ntotalPages: {total_pages}"
                f"\npageSize: {size_resp}"
                f"\nhasNext: {has_next}"
            )

            if total_esperado is None:
                total_esperado = total
            elif total != total_esperado:
                raise PaginacaoInconsistenteError(
                    f"totalItems mudou durante a paginação: "
                    f"{total_esperado} -> {total} (página {pagina})."
                )

            tamanho = size_resp or page_size
            paginas_esperadas = math.ceil(total_esperado / tamanho)

            if total_pages is not None and total_pages != paginas_esperadas:
                raise PaginacaoInconsistenteError(
                    f"totalPages={total_pages} não confere com "
                    f"totalItems={total_esperado} e pageSize={tamanho}."
                )

            registros.extend(items)

            if chave_contagem is not None:
                for item in items:
                    valores = tuple(item.get(campo) for campo in chave_contagem)

                    if any(valor is None for valor in valores):
                        raise PaginacaoInconsistenteError(
                            f"Chave de contagem incompleta na página {pagina}: "
                            f"{valores}."
                        )

                    chaves_encontradas.add(valores)

            quantidade = quantidade_validada()

            if not items and quantidade < total_esperado:
                raise PaginacaoInconsistenteError(
                    f"Página {pagina} vazia. "
                    f"Total validado: {quantidade}/{total_esperado}."
                )

            continua = pagina < paginas_esperadas

            if has_next is not None and has_next != continua:
                raise PaginacaoInconsistenteError(
                    f"hasNext={has_next} contradiz a página "
                    f"{pagina} de {paginas_esperadas}."
                )

            print(
                f"Página {pagina}/{max(paginas_esperadas, 1)}: "
                f"{len(items)} linhas | "
                f"{quantidade} registros validados"
            )

            if not continua:
                break

            pagina += 1
            
        print("CHAVE DE CONTAGEM:", chave_contagem)
        print("TOTAL DE LINHAS:", len(registros))
        print("TOTAL DE NUM_EMpenho DISTINTOS:", len({
            item.get("num_empenho")
            for item in registros
        }))
        print("TOTAL DE CHAVES VALIDADAS:", len(chaves_encontradas))

        quantidade_final = quantidade_validada()

        if quantidade_final != total_esperado:
            raise PaginacaoInconsistenteError(
                f"Paginação incompleta: {quantidade_final} de "
                f"{total_esperado} registros validados. "
                f"Linhas recebidas: {len(registros)}."
            )

        print(
            f"Total coletado: {len(registros)} linhas | "
            f"{quantidade_final} registros validados"
        )

        return registros


    def buscar_favorecidos(
        self,
        *,
        ano: int,
        page_size: int = 50,
        **filtros,
    ) -> pd.DataFrame:
        """
        Extrai os favorecidos agregados.
        """

        registros = self.buscar_todas_paginas(
            ano=ano,
            tipo_retorno="favorecido",
            page_size=page_size,
            **filtros,
        )

        return pd.DataFrame(registros)

    @staticmethod
    def remover_duplicatas_empenhos(
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, int]:
        """
        Remove duplicatas exatas e valida a identidade do empenho.

        A identidade considera:
        ano_exercicio, cod_orgao, cod_uo, num_empenho e num_processo.

        Registros sem os campos necessários para identificar o empenho
        não são descartados: geram erro para investigação.
        """

        if df.empty:
            return df, 0

        chave = [
            "ano_exercicio",
            "cod_orgao",
            "cod_uo",
            "num_empenho",
            "num_processo",
        ]

        # Verifica se todas as colunas necessárias existem.
        colunas_ausentes = [
            coluna for coluna in chave
            if coluna not in df.columns
        ]

        if colunas_ausentes:
            raise DuplicidadeConflitanteError(
                "Não foi possível validar a identidade dos empenhos. "
                f"Colunas ausentes: {colunas_ausentes}."
            )

        # Remove somente registros completamente idênticos.
        exatas = df.duplicated(keep="first")
        removidas = int(exatas.sum())

        df = df.loc[~exatas].copy()

        # Verifica campos nulos ou vazios na chave de identificação.
        campos_invalidos = pd.DataFrame(index=df.index)

        for coluna in chave:
            invalidos = df[coluna].isna()

            if pd.api.types.is_string_dtype(df[coluna]):
                invalidos |= df[coluna].str.strip().eq("")

            campos_invalidos[coluna] = invalidos

        linhas_invalidas = campos_invalidos.any(axis=1)

        if linhas_invalidas.any():
            exemplos = df.loc[
                linhas_invalidas,
                chave
            ].head(5)

            raise DuplicidadeConflitanteError(
                f"{int(linhas_invalidas.sum())} registros possuem "
                "campos ausentes ou vazios na chave de identificação. "
                f"Campos: {chave}. "
                f"Exemplos: {exemplos.to_dict(orient='records')}."
            )

        # Identifica conflitos na chave completa.
        conflitos = df.duplicated(
            subset=chave,
            keep=False
        )

        if conflitos.any():
            grupos = df.loc[conflitos].groupby(
                chave,
                dropna=False
            )

            for identificador, registros_grupo in grupos:
                if len(registros_grupo) <= 1:
                    continue

                divergentes = [
                    coluna
                    for coluna in df.columns
                    if registros_grupo[coluna].nunique(
                        dropna=False
                    ) > 1
                ]

                if divergentes:
                    print("\nDUPLICIDADE CONFLITANTE")
                    print(f"Chave: {identificador}")
                    print(f"Colunas divergentes: {divergentes}")

                    colunas_exibicao = list(
                        dict.fromkeys(chave + divergentes)
                    )

                    print(
                        registros_grupo[colunas_exibicao]
                        .to_string(index=False)
                    )

                    break

            raise DuplicidadeConflitanteError(
                f"{int(conflitos.sum())} linhas compartilham "
                f"a chave {chave} com conteúdos diferentes."
            )

        return df.reset_index(drop=True), removidas

    def buscar_empenhos(
        self,
        *,
        ano: int,
        cpf_cnpj: str,
        page_size: int = 50,
        **filtros,
    ) -> pd.DataFrame:
        """
        Extrai os empenhos detalhados de um favorecido.

        O DataFrame devolvido traz em ``df.attrs["duplicatas_removidas"]``
        o número de linhas idênticas descartadas.
        """

        filtros = {
            **filtros,
            "cpf_cnpj_favorecido": cpf_cnpj,
        }

        registros = self.buscar_todas_paginas(
            ano=ano,
            tipo_retorno="favorecido",
            page_size=page_size,
            chave_contagem=None,
            **filtros,
        )

        df = pd.DataFrame(registros)

        df, removidas = self.remover_duplicatas_empenhos(df)
        df.attrs["duplicatas_removidas"] = removidas

        if removidas:
            print(f"Duplicatas exatas removidas: {removidas}")

        return df

    # ------------------------------------------------------------------
    # Gravação
    # ------------------------------------------------------------------

    @staticmethod
    def salvar_csv(
        df: pd.DataFrame,
        caminho: str | Path,
        *,
        permitir_vazio: bool = False,
    ) -> None:
        """
        Salva DataFrame em CSV de forma atômica.

        Escreve em arquivo temporário na mesma pasta, confere a
        quantidade de linhas relendo o arquivo e só então substitui o
        destino. Em caso de falha, o arquivo existente permanece intacto.
        DataFrame vazio é recusado, salvo ``permitir_vazio=True``.
        """

        caminho = Path(caminho)

        if df.empty and not permitir_vazio:
            raise ValueError(
                "DataFrame vazio: gravação recusada para não sobrescrever "
                f"um arquivo possivelmente válido ({caminho.name})."
            )

        caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        descritor, nome_tmp = tempfile.mkstemp(
            prefix=f".{caminho.name}.",
            suffix=".tmp",
            dir=caminho.parent,
        )
        os.close(descritor)
        tmp = Path(nome_tmp)

        try:
            df.to_csv(
                tmp,
                index=False,
                encoding="utf-8-sig",
            )

            relido = pd.read_csv(tmp, dtype=str, encoding="utf-8-sig")

            if len(relido) != len(df):
                raise OSError(
                    f"Verificação falhou: gravadas {len(relido)} linhas, "
                    f"esperadas {len(df)}."
                )

            os.replace(tmp, caminho)

        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

        print(
            f"Arquivo salvo: {caminho}"
        )

        print(
            f"Registros: {len(df)}"
        )
