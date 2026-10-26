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
        **filtros,
    ) -> list[dict[str, Any]]:
        """
        Busca todas as páginas e só devolve o resultado se a paginação
        estiver completa e coerente com os totais informados pela API.

        Lista vazia significa SOMENTE "consulta válida com zero
        registros" (totalItems == 0). Qualquer outra situação
        incompatível levanta uma exceção.
        """

        registros: list[dict[str, Any]] = []
        total_esperado: int | None = None
        pagina = 1

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
                    f"totalItems={total_esperado} e pageSize={tamanho} "
                    f"(esperado {paginas_esperadas})."
                )

            if not items and total_esperado > len(registros):
                raise PaginacaoInconsistenteError(
                    f"Página {pagina} vazia, mas a API informa "
                    f"{total_esperado} registros e só {len(registros)} "
                    f"foram recebidos."
                )

            registros.extend(items)

            if len(registros) > total_esperado:
                raise PaginacaoInconsistenteError(
                    f"Recebidos {len(registros)} registros, mais do que "
                    f"os {total_esperado} informados pela API."
                )

            continua = pagina < paginas_esperadas

            if has_next is not None and has_next != continua:
                raise PaginacaoInconsistenteError(
                    f"hasNext={has_next} contradiz a página {pagina} de "
                    f"{paginas_esperadas}."
                )

            print(
                f"Página {pagina}/{max(paginas_esperadas, 1)}: "
                f"{len(items)} registros"
            )

            if not continua:
                break

            pagina += 1

        if len(registros) != total_esperado:
            raise PaginacaoInconsistenteError(
                f"Paginação incompleta: {len(registros)} de "
                f"{total_esperado} registros."
            )

        print(f"Total coletado: {len(registros)} (esperado {total_esperado})")

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
        Remove linhas idênticas repetidas entre páginas.

        A chave do empenho é (ano_exercicio, cod_uo, num_empenho), usando
        as colunas existentes. Duplicata exata é descartada; a mesma chave
        com conteúdo diferente levanta DuplicidadeConflitanteError, pois
        descartar um dos registros seria perda silenciosa de dados.
        """

        chave = [c for c in CHAVE_EMPENHO if c in df.columns]

        if "num_empenho" not in chave or df.empty:
            return df, 0

        exatas = df.duplicated(keep="first")
        removidas = int(exatas.sum())
        df = df.loc[~exatas]

        conflitos = df.duplicated(subset=chave, keep=False)

        if conflitos.any():
            exemplo = df.loc[conflitos, chave].iloc[0].to_dict()
            raise DuplicidadeConflitanteError(
                f"{int(conflitos.sum())} linhas compartilham a chave "
                f"{chave} com conteúdos diferentes. Exemplo: {exemplo}."
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
