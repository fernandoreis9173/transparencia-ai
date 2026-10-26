import json

import pytest

from src.api.scripts import despesas_extractor as de


class FakeResponse:
    def __init__(self, corpo=None, status=200, json_invalido=False):
        self._corpo = corpo
        self.status_code = status
        self._json_invalido = json_invalido

    def json(self):
        if self._json_invalido:
            raise json.JSONDecodeError("inválido", "<html>", 0)
        return self._corpo


class FakeSession:
    """Sessão simulada. ``respostas`` é uma função payload -> FakeResponse,
    um FakeResponse fixo ou uma exceção a ser levantada."""

    def __init__(self, respostas):
        self.respostas = respostas
        self.headers = {}
        self.chamadas = []

    def post(self, url, json=None, timeout=None):
        self.chamadas.append(json)
        r = self.respostas(json) if callable(self.respostas) else self.respostas
        if isinstance(r, Exception):
            raise r
        return r


def pagina_api(registros, payload, **sobrescrever):
    """Resposta no contrato real: items/totalItems/totalPages/hasNext."""
    tamanho = payload["pageSize"]
    pagina = payload["page"]
    total = len(registros)
    paginas = -(-total // tamanho)
    ini = (pagina - 1) * tamanho
    corpo = {
        "items": registros[ini:ini + tamanho],
        "totalItems": total,
        "totalPages": paginas,
        "hasNext": pagina < paginas,
        "pageSize": tamanho,
    }
    corpo.update(sobrescrever)
    return FakeResponse(corpo)


def empenhos(n, uo="48057", ano=2025, cpf="32691514000127", prefixo="2025NE"):
    return [
        {
            "ano_exercicio": ano,
            "cod_uo": uo,
            "num_empenho": f"{prefixo}{i:05d}",
            "cnpj_cpf_favorecido": cpf,
            "nome_favorecido": "EMPRESA X",
            "vl_empenhado": 100.0 + i,
        }
        for i in range(n)
    ]


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    monkeypatch.setattr(de.time, "sleep", lambda *_: None)


@pytest.fixture
def extrator():
    def criar(respostas, max_retries=1):
        e = de.DespesasExtractor(timeout=1, max_retries=max_retries, delay=0)
        e.session = FakeSession(respostas)
        return e

    return criar
