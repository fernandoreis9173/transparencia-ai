from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests


class DespesasExtractor:
    """
    Extrator reutilizável dos dados de despesas públicas
    do Portal da Transparência do Estado de São Paulo.
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

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Executa uma requisição POST com retry.
        """

        last_error = None

        for attempt in range(1, self.max_retries + 1):

            try:
                response = self.session.post(
                    self.ENDPOINT_BUSCAR,
                    json=payload,
                    timeout=self.timeout,
                )

                response.raise_for_status()

                return response.json()

            except (
                requests.RequestException,
                ValueError,
            ) as error:

                last_error = error

                print(
                    f"Erro na requisição "
                    f"(tentativa {attempt}/{self.max_retries}): "
                    f"{error}"
                )

                if attempt < self.max_retries:
                    time.sleep(attempt * 2)

        raise RuntimeError(
            f"Falha após {self.max_retries} tentativas"
        ) from last_error

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

    @staticmethod
    def _extrair_registros(resultado: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extrai a lista de registros da resposta.

        A API pode utilizar diferentes propriedades dependendo
        da etapa da consulta.
        """

        for chave in (
            "dados",
            "data",
            "items",
            "resultado",
            "registros",
        ):
            valor = resultado.get(chave)

            if isinstance(valor, list):
                return valor

        return []

    @staticmethod
    def _total_itens(resultado: dict[str, Any]) -> int:
        """
        Obtém o total de registros retornado pela API.
        """

        for chave in (
            "totalItens",
            "total",
            "totalItems",
        ):
            valor = resultado.get(chave)

            if valor is not None:
                try:
                    return int(valor)
                except (TypeError, ValueError):
                    pass

        return 0

    def buscar_todas_paginas(
        self,
        *,
        ano: int,
        tipo_retorno: str,
        page_size: int = 50,
        **filtros,
    ) -> list[dict[str, Any]]:
        """
        Busca automaticamente todas as páginas.
        """

        primeira_resposta = self.consultar(
            ano=ano,
            tipo_retorno=tipo_retorno,
            page=1,
            page_size=page_size,
            **filtros,
        )

        registros = self._extrair_registros(primeira_resposta)

        total_itens = self._total_itens(primeira_resposta)

        if total_itens == 0:
            total_itens = len(registros)

        total_paginas = max(
            1,
            (total_itens + page_size - 1) // page_size,
        )

        print(
            f"Total de registros: {total_itens}"
        )

        print(
            f"Total de páginas: {total_paginas}"
        )

        print(
            f"Página 1/{total_paginas}: "
            f"{len(registros)} registros"
        )

        for page in range(2, total_paginas + 1):

            resposta = self.consultar(
                ano=ano,
                tipo_retorno=tipo_retorno,
                page=page,
                page_size=page_size,
                **filtros,
            )

            pagina = self._extrair_registros(resposta)

            registros.extend(pagina)

            print(
                f"Página {page}/{total_paginas}: "
                f"{len(pagina)} registros"
            )

        print(
            f"Total coletado: {len(registros)}"
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

        if not df.empty:
            df = df.drop_duplicates(
                subset=["num_empenho"],
                keep="first",
            )

        return df

    @staticmethod
    def salvar_csv(
        df: pd.DataFrame,
        caminho: str | Path,
    ) -> None:
        """
        Salva DataFrame em CSV.
        """

        caminho = Path(caminho)

        caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        df.to_csv(
            caminho,
            index=False,
            encoding="utf-8-sig",
        )

        print(
            f"Arquivo salvo: {caminho}"
        )

        print(
            f"Registros: {len(df)}"
        )