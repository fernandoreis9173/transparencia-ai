import pandas as pd
import pytest
import requests

from src.api.scripts import despesas_extractor as de
from tests.conftest import FakeResponse, empenhos, pagina_api

CPF = "32691514000127"


def buscar(extrator, registros, page_size=5, **sobrescrever):
    e = extrator(lambda p: pagina_api(registros, p, **sobrescrever))
    return e.buscar_todas_paginas(
        ano=2025, tipo_retorno="favorecido", page_size=page_size
    )


def buscar_resposta(extrator, resposta, **kw):
    return extrator(resposta).buscar_todas_paginas(
        ano=2025, tipo_retorno="favorecido", **kw
    )


# 1-3 ---------------------------------------------------------------
def test_uma_pagina_com_registros(extrator):
    assert len(buscar(extrator, empenhos(3))) == 3


def test_multiplas_paginas_ultima_menor(extrator):
    r = buscar(extrator, empenhos(11), page_size=5)  # 5 + 5 + 1
    assert [x["num_empenho"] for x in r] == [
        x["num_empenho"] for x in empenhos(11)
    ]


# 4 -----------------------------------------------------------------
def test_consulta_valida_sem_resultados(extrator):
    resp = FakeResponse(
        {"items": [], "totalItems": 0, "totalPages": 0, "hasNext": False}
    )
    assert buscar_resposta(extrator, resp) == []


# 5-7 ---------------------------------------------------------------
def test_total_ausente(extrator):
    with pytest.raises(de.RespostaInvalidaError, match="totalItems"):
        buscar_resposta(extrator, FakeResponse({"items": empenhos(2)}))


@pytest.mark.parametrize("total", ["abc", -1, None, True, 1.5])
def test_total_invalido(extrator, total):
    resp = FakeResponse({"items": empenhos(2), "totalItems": total})
    with pytest.raises(de.RespostaInvalidaError):
        buscar_resposta(extrator, resp)


@pytest.mark.parametrize(
    "corpo",
    [
        {"dados": [1], "totalItems": 1},  # chave diferente da esperada
        {"items": "texto", "totalItems": 1},  # items não é lista
        {"items": [1, 2], "totalItems": 2},  # elementos não são objetos
        {},
    ],
)
def test_estrutura_inesperada_nao_vira_lista_vazia(extrator, corpo):
    with pytest.raises(de.RespostaInvalidaError):
        buscar_resposta(extrator, FakeResponse(corpo))


def test_json_que_nao_e_objeto(extrator):
    with pytest.raises(de.RespostaInvalidaError):
        buscar_resposta(extrator, FakeResponse([{"a": 1}]))


# 8-10 --------------------------------------------------------------
def test_erro_http(extrator):
    with pytest.raises(de.ErroHTTP, match="500"):
        buscar_resposta(extrator, FakeResponse({}, status=500))


def test_http_4xx_nao_repete(extrator):
    e = extrator(FakeResponse({}, status=404), max_retries=3)
    with pytest.raises(de.ErroHTTP):
        e.consultar(ano=2025)
    assert len(e.session.chamadas) == 1


def test_http_5xx_repete_ate_o_limite(extrator):
    e = extrator(FakeResponse({}, status=503), max_retries=3)
    with pytest.raises(de.ErroHTTP):
        e.consultar(ano=2025)
    assert len(e.session.chamadas) == 3


def test_erro_de_conexao(extrator):
    with pytest.raises(de.ErroRede):
        buscar_resposta(extrator, requests.ConnectionError("sem rede"))


def test_falha_de_decodificacao_json(extrator):
    with pytest.raises(de.ErroDecodificacao):
        buscar_resposta(extrator, FakeResponse(json_invalido=True))


# 11-12 -------------------------------------------------------------
def test_pagina_vazia_inesperada(extrator):
    regs = empenhos(11)

    def resp(p):
        if p["page"] == 2:
            return FakeResponse(
                {"items": [], "totalItems": 11, "totalPages": 3,
                 "hasNext": True, "pageSize": 5}
            )
        return pagina_api(regs, p)

    with pytest.raises(de.PaginacaoInconsistenteError, match="vazia"):
        buscar_resposta(extrator, resp, page_size=5)


def test_divergencia_entre_total_esperado_e_recebido(extrator):
    # A API diz 11 itens, mas só entrega 10 e encerra a paginação.
    regs = empenhos(10)

    def resp(p):
        return pagina_api(regs, p, totalItems=11, totalPages=3)

    with pytest.raises(de.PaginacaoInconsistenteError):
        buscar_resposta(extrator, resp, page_size=5)


def test_total_muda_durante_a_paginacao(extrator):
    regs = empenhos(11)

    def resp(p):
        extra = {"totalItems": 12, "totalPages": 3} if p["page"] == 2 else {}
        return pagina_api(regs, p, **extra)

    with pytest.raises(de.PaginacaoInconsistenteError, match="mudou"):
        buscar_resposta(extrator, resp, page_size=5)


def test_totalpages_incoerente(extrator):
    with pytest.raises(de.PaginacaoInconsistenteError, match="totalPages"):
        buscar(extrator, empenhos(11), totalPages=7)


def test_hasnext_contradiz_paginas(extrator):
    with pytest.raises(de.PaginacaoInconsistenteError, match="hasNext"):
        buscar(extrator, empenhos(11), hasNext=False)


def test_mais_registros_que_o_total(extrator):
    with pytest.raises(de.PaginacaoInconsistenteError):
        buscar(extrator, empenhos(3), totalItems=1, totalPages=1)


# 13 ----------------------------------------------------------------
def test_duplicatas_exatas_entre_paginas_sao_removidas(extrator):
    regs = empenhos(5) + empenhos(5)[:2]  # 2 linhas repetidas exatamente
    e = extrator(lambda p: pagina_api(regs, p))
    df = e.buscar_empenhos(ano=2025, cpf_cnpj=CPF, page_size=5)
    assert len(df) == 5
    assert df.attrs["duplicatas_removidas"] == 2


def test_mesmo_num_empenho_em_unidades_diferentes_nao_e_duplicata(extrator):
    regs = empenhos(2, uo="48057") + empenhos(2, uo="48058")
    e = extrator(lambda p: pagina_api(regs, p))
    df = e.buscar_empenhos(ano=2025, cpf_cnpj=CPF, page_size=5)
    assert len(df) == 4


def test_mesma_chave_com_conteudo_diferente_levanta_erro(extrator):
    a = empenhos(1)[0]
    b = {**a, "vl_empenhado": 999.0}
    e = extrator(lambda p: pagina_api([a, b], p))
    with pytest.raises(de.DuplicidadeConflitanteError):
        e.buscar_empenhos(ano=2025, cpf_cnpj=CPF)


# 16 ----------------------------------------------------------------
def test_falha_ao_gravar_preserva_csv_e_limpa_temporarios(tmp_path, monkeypatch):
    destino = tmp_path / "x.csv"
    pd.DataFrame({"a": [1, 2, 3]}).to_csv(destino, index=False)
    antes = destino.read_bytes()

    def quebrar(self, *a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(pd.DataFrame, "to_csv", quebrar)

    with pytest.raises(OSError):
        de.DespesasExtractor.salvar_csv(pd.DataFrame({"a": [9]}), destino)

    assert destino.read_bytes() == antes
    assert [p.name for p in tmp_path.iterdir()] == ["x.csv"]


def test_salvar_csv_recusa_vazio(tmp_path):
    destino = tmp_path / "x.csv"
    pd.DataFrame({"a": [1]}).to_csv(destino, index=False)

    with pytest.raises(ValueError):
        de.DespesasExtractor.salvar_csv(pd.DataFrame(), destino)

    assert len(pd.read_csv(destino)) == 1


def test_salvar_csv_ok(tmp_path):
    destino = tmp_path / "sub" / "x.csv"
    de.DespesasExtractor.salvar_csv(pd.DataFrame({"a": [1, 2]}), destino)

    assert len(pd.read_csv(destino, encoding="utf-8-sig")) == 2
    assert [p.name for p in destino.parent.iterdir()] == ["x.csv"]
