import hashlib
import json

import pandas as pd
import pytest

from src.api.scripts import despesas_extractor as de
from src.api.scripts import extrair_empenhos_2025 as ex

CPF_A = "11111111111"
CPF_B = "22222222222222"
CPF_C = "33333333333"
CPF_D = "44444444444"


class ExtratorFalso:
    """Stub de DespesasExtractor. ``comportamento[cpf]`` é um DataFrame ou
    uma exceção a ser levantada; CPFs ausentes retornam DataFrame vazio."""

    salvar_csv = staticmethod(de.DespesasExtractor.salvar_csv)

    def __init__(self, comportamento):
        self.comportamento = comportamento
        self.consultados = []

    def buscar_empenhos(self, *, ano, cpf_cnpj, **_):
        self.consultados.append(cpf_cnpj)
        r = self.comportamento.get(cpf_cnpj, pd.DataFrame())
        if isinstance(r, Exception):
            raise r
        return r


def df_emp(cpf, n=2):
    return pd.DataFrame(
        [
            {
                "cnpj_cpf_favorecido": cpf,
                "nome_favorecido": "X",
                "ano_exercicio": 2025,
                "cod_uo": "1",
                "num_empenho": f"2025NE{i}",
            }
            for i in range(n)
        ]
    )


def favorecidos(*cpfs, nomes=None):
    nomes = nomes or [f"Nome {i}" for i in range(len(cpfs))]
    return pd.DataFrame(
        {"cnpj_cpf_favorecido": list(cpfs), "nome_favorecido": nomes}
    )


@pytest.fixture
def caminhos(tmp_path):
    return {
        "empenhos_dir": tmp_path / "emp",
        "checkpoint_file": tmp_path / "cp" / "cp.json",
    }


def rodar(df, extrator, caminhos, **kw):
    return ex.executar(df, extrator, **caminhos, **kw)


def checkpoint(caminhos):
    return json.loads(
        caminhos["checkpoint_file"].read_text(encoding="utf-8")
    )


# 14-15 -------------------------------------------------------------
@pytest.mark.parametrize(
    "valor",
    [None, float("nan"), "", "  ", "nan", "None", "null", "NaN",
     "123456789", "abc12345678", "1234567890123"],
)
def test_identificador_invalido_nao_e_enviado_a_api(valor, caminhos):
    ext = ExtratorFalso({})
    r = rodar(favorecidos(valor), ext, caminhos)

    assert ext.consultados == []
    assert r["ignorados"] == 1 and r["tentados"] == 0 and r["com_dados"] == 0

    reg = checkpoint(caminhos)["registros"]["0"]
    assert reg["status"] == ex.IGNORADO and reg["cpf_cnpj"] is None
    assert list(caminhos["empenhos_dir"].iterdir()) == []


def test_cpf_de_9_digitos_nao_recebe_zeros():
    assert ex.validar_cpf_cnpj("123456789") == (
        None, "tamanho inválido (9 dígitos)"
    )


def test_pontuacao_e_removida_de_identificador_valido():
    assert ex.validar_cpf_cnpj("111.111.111-11") == ("11111111111", None)
    assert ex.validar_cpf_cnpj("12.345.678/0001-95") == (
        "12345678000195", None
    )


@pytest.mark.parametrize("nome", [None, float("nan"), "", "nan"])
def test_nome_ausente(nome):
    assert ex.normalizar_nome(nome) == ("Não informado", True)


def test_nome_ausente_nao_vira_nan_no_csv(caminhos):
    df = df_emp(CPF_A).drop(columns=["nome_favorecido"])
    rodar(favorecidos(CPF_A, nomes=[None]), ExtratorFalso({CPF_A: df}), caminhos)

    csv = pd.read_csv(
        caminhos["empenhos_dir"] / f"{CPF_A}.csv",
        dtype=str, encoding="utf-8-sig",
    )
    assert set(csv["nome_favorecido"]) == {"Não informado"}


# estados ------------------------------------------------------------
def test_estados_com_dados_sem_dados_ignorado_falha(caminhos):
    ext = ExtratorFalso(
        {CPF_A: df_emp(CPF_A), CPF_B: pd.DataFrame(), CPF_C: de.ErroRede("x")}
    )
    r = rodar(favorecidos(CPF_A, CPF_B, None, CPF_C), ext, caminhos)

    st = {k: v["status"] for k, v in checkpoint(caminhos)["registros"].items()}
    assert st == {
        "0": ex.COM_DADOS, "1": ex.SEM_DADOS,
        "2": ex.IGNORADO, "3": ex.FALHA,
    }
    assert (r["com_dados"], r["sem_dados"], r["ignorados"], r["falhas"]) == (
        1, 1, 1, 1
    )
    assert r["arquivos_gravados"] == 1 and r["falhas_pendentes"] == 1
    assert not r["completo"]


def test_sem_dados_nao_cria_arquivo(caminhos):
    rodar(favorecidos(CPF_B), ExtratorFalso({}), caminhos)
    assert list(caminhos["empenhos_dir"].iterdir()) == []


def test_csv_de_outro_favorecido_e_falha(caminhos):
    ext = ExtratorFalso({CPF_A: df_emp("99999999999")})
    rodar(favorecidos(CPF_A), ext, caminhos)

    reg = checkpoint(caminhos)["registros"]["0"]
    assert reg["status"] == ex.FALHA and "outro favorecido" in reg["erro"]
    assert list(caminhos["empenhos_dir"].iterdir()) == []


# 17-18 -------------------------------------------------------------
def test_interrupcao_e_retomada(caminhos):
    df = favorecidos(CPF_A, CPF_B, CPF_C)
    ext = ExtratorFalso(
        {CPF_A: df_emp(CPF_A), CPF_B: df_emp(CPF_B), CPF_C: df_emp(CPF_C)}
    )
    r1 = rodar(df, ext, caminhos, limite=2)
    assert r1["indice_retomada"] == 2 and not r1["completo"]
    assert r1["motivo_parada"] == "limite da execução atingido"

    ext2 = ExtratorFalso({CPF_C: df_emp(CPF_C)})
    r2 = rodar(df, ext2, caminhos, limite=2)

    assert ext2.consultados == [CPF_C]  # não repete A e B
    assert r2["completo"] and r2["indice_retomada"] == 3


def test_falha_nao_e_concluida_e_so_reprocessa_quando_pedido(caminhos):
    df = favorecidos(CPF_A, CPF_B)
    ext = ExtratorFalso({CPF_A: de.ErroHTTP("HTTP 500"), CPF_B: df_emp(CPF_B)})
    r1 = rodar(df, ext, caminhos)

    cp = checkpoint(caminhos)
    assert cp["registros"]["0"]["status"] == ex.FALHA
    assert cp["registros"]["0"]["tentativas"] == 1
    assert cp["processados"] == 1 and len(cp["falhas"]) == 1
    assert not r1["completo"] and "pendente" in r1["motivo_parada"]

    # Execução normal não repete a falha.
    ext2 = ExtratorFalso({CPF_A: df_emp(CPF_A)})
    rodar(df, ext2, caminhos)
    assert ext2.consultados == []

    # Somente o reprocessamento explícito a repete.
    r3 = rodar(df, ext2, caminhos, reprocessar_falhas=True)
    cp = checkpoint(caminhos)
    assert ext2.consultados == [CPF_A]
    assert cp["registros"]["0"]["status"] == ex.COM_DADOS
    assert cp["registros"]["0"]["tentativas"] == 2
    assert cp["falhas"] == [] and r3["completo"]


def test_falha_repetida_nao_duplica_historico(caminhos):
    df = favorecidos(CPF_A)
    ext = ExtratorFalso({CPF_A: de.ErroRede("x")})

    rodar(df, ext, caminhos)
    rodar(df, ext, caminhos, reprocessar_falhas=True)
    rodar(df, ext, caminhos, reprocessar_falhas=True)

    cp = checkpoint(caminhos)
    assert len(cp["falhas"]) == 1
    assert cp["registros"]["0"]["tentativas"] == 3


def test_interrompe_apos_falhas_consecutivas(caminhos):
    cpfs = [f"{i:011d}" for i in range(1, 9)]
    ext = ExtratorFalso({c: de.ErroRede("fora") for c in cpfs})
    r = rodar(favorecidos(*cpfs), ext, caminhos, falhas_consecutivas_max=3)

    assert len(ext.consultados) == 3
    assert "consecutivas" in r["motivo_parada"]


# 19 ----------------------------------------------------------------
def test_checkpoint_antigo_v1_e_migrado_com_backup(caminhos):
    v1 = {
        "indice": 3, "processados": 2, "erros": 1,
        "inicio": "2026-10-07T14:07:47",
        "ultima_atualizacao": "2026-10-07T15:19:50",
        "falhas": [
            {"indice": 1, "cpf_cnpj": CPF_B, "nome": "N", "erro": "boom"}
        ],
    }
    cp_file = caminhos["checkpoint_file"]
    cp_file.parent.mkdir(parents=True)
    cp_file.write_text(json.dumps(v1), encoding="utf-8")
    original = cp_file.read_bytes()

    df = favorecidos(CPF_A, CPF_B, CPF_C, CPF_D)
    ext = ExtratorFalso({CPF_D: df_emp(CPF_D)})
    rodar(df, ext, caminhos, limite=5)

    assert ext.consultados == [CPF_D]  # retoma do índice 3

    backups = list(cp_file.parent.glob("cp.json.bak-v1-*"))
    assert len(backups) == 1 and backups[0].read_bytes() == original

    cp = checkpoint(caminhos)
    assert cp["versao"] == 2
    assert cp["registros"]["0"]["status"] == ex.LEGADO
    assert cp["registros"]["1"]["status"] == ex.FALHA
    assert cp["registros"]["1"]["erro"] == "boom"
    assert cp["registros"]["3"]["status"] == ex.COM_DADOS
    assert cp["inicio"] == "2026-10-07T14:07:47"


def test_migracao_preserva_chaves_do_v1():
    cp = ex.migrar_checkpoint(
        {"indice": 2, "processados": 2, "erros": 0, "falhas": []}
    )
    assert {
        "indice", "processados", "erros", "inicio",
        "ultima_atualizacao", "falhas",
    } <= set(cp)


# 20 ----------------------------------------------------------------
def test_limite_nao_processa_alem_do_limite(caminhos):
    cpfs = [f"{i:011d}" for i in range(1, 11)]
    ext = ExtratorFalso({c: df_emp(c) for c in cpfs})
    r = rodar(favorecidos(*cpfs), ext, caminhos, limite=4)

    assert ext.consultados == cpfs[:4]
    assert r["indice_retomada"] == 4 and not r["completo"]
    assert checkpoint(caminhos)["indice"] == 4


def test_limite_invalido(caminhos):
    with pytest.raises(ValueError):
        rodar(favorecidos(CPF_A), ExtratorFalso({}), caminhos, limite=0)


def test_relatorio_nao_afirma_conclusao_quando_parcial(capsys):
    r = ex._resumo_vazio()
    r.update(
        total_entrada=10, indice_retomada=3,
        motivo_parada="limite da execução atingido",
    )
    ex.imprimir_relatorio(r, "teste")

    saida = capsys.readouterr().out
    assert "EXECUÇÃO PARCIAL" in saida
    assert "EXTRAÇÃO COMPLETA" not in saida


# 21 ----------------------------------------------------------------
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def preparar_main(tmp_path, monkeypatch, comportamento):
    prod_cp = tmp_path / "prod" / "cp.json"
    prod_emp = tmp_path / "prod" / "empenhos"
    fav = tmp_path / "fav.csv"
    favorecidos(CPF_A, CPF_B).to_csv(fav, index=False)

    monkeypatch.setattr(ex, "FAVORECIDOS_FILE", fav)
    monkeypatch.setattr(ex, "CHECKPOINT_FILE", prod_cp)
    monkeypatch.setattr(ex, "EMPENHOS_DIR", prod_emp)
    monkeypatch.setattr(ex, "TESTE_DIR", tmp_path / "teste")
    monkeypatch.setattr(
        ex, "DespesasExtractor", lambda **_: ExtratorFalso(comportamento)
    )
    return prod_cp, prod_emp


def test_modo_teste_nao_altera_checkpoint_nem_csvs_de_producao(
    tmp_path, monkeypatch
):
    prod_cp, prod_emp = preparar_main(
        tmp_path, monkeypatch,
        {CPF_A: df_emp(CPF_A), CPF_B: df_emp(CPF_B)},
    )
    prod_cp.parent.mkdir(parents=True)
    prod_emp.mkdir()
    prod_cp.write_text(
        json.dumps({"indice": 1, "processados": 1, "erros": 0, "falhas": []}),
        encoding="utf-8",
    )
    (prod_emp / "antigo.csv").write_text("a\n1\n", encoding="utf-8")
    h_cp, h_csv = sha(prod_cp), sha(prod_emp / "antigo.csv")

    assert ex.main(["--limite", "2"]) == 0  # modo teste é o padrão

    assert sha(prod_cp) == h_cp
    assert sha(prod_emp / "antigo.csv") == h_csv
    assert [p.name for p in prod_emp.iterdir()] == ["antigo.csv"]
    assert (tmp_path / "teste" / "checkpoints" / ex.NOME_CHECKPOINT).exists()
    assert (tmp_path / "teste" / "empenhos" / f"{CPF_A}.csv").exists()


def test_modo_producao_usa_checkpoint_oficial(tmp_path, monkeypatch):
    prod_cp, _ = preparar_main(
        tmp_path, monkeypatch, {CPF_A: df_emp(CPF_A)}
    )
    ex.main(["--modo", "producao", "--limite", "1"])

    assert checkpoint({"checkpoint_file": prod_cp})["indice"] == 1


def test_argumentos_padrao_e_inicio_somente_no_teste():
    with pytest.raises(SystemExit):
        ex.ler_argumentos(["--modo", "producao", "--inicio", "5"])

    padrao = ex.ler_argumentos([])
    assert padrao.modo == "teste" and padrao.limite == ex.LIMITE_PADRAO
