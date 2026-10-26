"""
Extração de empenhos por favorecido (2025, órgão 48000, função 12).

Execução (a partir da raiz do repositório):

    python -m src.api.scripts.extrair_empenhos_2025 --limite 5

ou, a partir de ``src``:

    python -m api.scripts.extrair_empenhos_2025 --limite 5

O modo padrão é ``teste``: usa diretório e checkpoint ISOLADOS em
``data/output/teste`` e nunca altera o checkpoint oficial. O modo
``producao`` precisa ser pedido explicitamente e continua limitado por
``--limite``.

Estados de cada favorecido (checkpoint v2, campo ``registros``):

    com_dados          consulta concluída, CSV gravado
    sem_dados          consulta válida, totalItems == 0
    ignorado_invalido  CPF/CNPJ ausente ou inválido (nunca enviado à API)
    falha              erro técnico; fica pendente até ser reprocessado
    concluido_legado   concluído por uma execução anterior ao checkpoint v2
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    from src.api.scripts.despesas_extractor import DespesasExtractor
except ImportError:  # execução a partir de ``src``
    from api.scripts.despesas_extractor import DespesasExtractor


ANO = 2025
COD_ORGAO = 48000
COD_FUNCAO = 12

PAGE_SIZE = 50

BASE_DIR = Path(__file__).resolve().parents[3]

RAW_DIR = BASE_DIR / "data" / "raw"

FAVORECIDOS_FILE = (
    RAW_DIR
    / "favorecidos_2025_orgao_48000_funcao_12.csv"
)

NOME_CHECKPOINT = "empenhos_2025_orgao_48000_funcao_12.json"

# Caminhos oficiais (produção)
EMPENHOS_DIR = RAW_DIR / "empenhos"

CHECKPOINT_DIR = BASE_DIR / "data" / "output" / "checkpoints"

CHECKPOINT_FILE = CHECKPOINT_DIR / NOME_CHECKPOINT

# Caminhos isolados (teste)
TESTE_DIR = BASE_DIR / "data" / "output" / "teste"

LIMITE_PADRAO = 100
FALHAS_CONSECUTIVAS_MAX = 5

COM_DADOS = "com_dados"
SEM_DADOS = "sem_dados"
IGNORADO = "ignorado_invalido"
FALHA = "falha"
LEGADO = "concluido_legado"

VAZIOS = {"", "nan", "none", "null", "<na>", "nat"}


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ----------------------------------------------------------------------
# Validação dos dados de entrada
# ----------------------------------------------------------------------

def validar_cpf_cnpj(valor) -> tuple[str | None, str | None]:
    """
    Devolve (identificador, motivo_da_rejeicao).

    Aceita somente 11 (CPF) ou 14 (CNPJ) dígitos. Pontuação comum
    (. - /) é removida. Identificadores com outro tamanho, como os de
    9 dígitos, NÃO são corrigidos com zeros à esquerda.
    """

    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return None, "ausente"

    texto = str(valor).strip()

    if texto.lower() in VAZIOS:
        return None, "ausente"

    limpo = re.sub(r"[.\-/\s]", "", texto)

    if not limpo.isdigit():
        return None, "contém caracteres não numéricos"

    if len(limpo) not in (11, 14):
        return None, f"tamanho inválido ({len(limpo)} dígitos)"

    return limpo, None


def normalizar_nome(valor) -> tuple[str, bool]:
    """Devolve (nome, ausente). Nome ausente vira 'Não informado'."""

    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return "Não informado", True

    texto = str(valor).strip()

    if texto.lower() in VAZIOS:
        return "Não informado", True

    return texto, False


# ----------------------------------------------------------------------
# Checkpoint (v2, compatível com o v1)
# ----------------------------------------------------------------------

def criar_checkpoint() -> dict:
    return {
        "versao": 2,
        "indice": 0,
        "processados": 0,
        "erros": 0,
        "inicio": agora(),
        "ultima_atualizacao": agora(),
        "registros": {},
        "falhas": [],
    }


def migrar_checkpoint(bruto: dict) -> dict:
    """
    Converte um checkpoint v1 em v2 SEM perder informação.

    No v1, todo índice abaixo de ``indice`` foi tentado. Os que constam
    em ``falhas`` continuam como falha pendente; os demais viram
    ``concluido_legado`` (não serão consultados de novo).
    """

    if bruto.get("versao") == 2:
        bruto.setdefault("registros", {})
        bruto.setdefault("falhas", [])
        return bruto

    cp = criar_checkpoint()
    cp["indice"] = int(bruto.get("indice", 0))
    cp["processados"] = int(bruto.get("processados", 0))
    cp["erros"] = int(bruto.get("erros", 0))
    cp["inicio"] = bruto.get("inicio", cp["inicio"])
    cp["ultima_atualizacao"] = bruto.get(
        "ultima_atualizacao", cp["ultima_atualizacao"]
    )

    falhas_v1 = {}
    for falha in bruto.get("falhas", []):
        falhas_v1[int(falha["indice"])] = falha

    for i in range(cp["indice"]):
        if i in falhas_v1:
            f = falhas_v1[i]
            cp["registros"][str(i)] = {
                "status": FALHA,
                "cpf_cnpj": f.get("cpf_cnpj"),
                "nome": f.get("nome"),
                "tentativas": 1,
                "erro": f.get("erro"),
                "atualizado_em": cp["ultima_atualizacao"],
            }
        else:
            cp["registros"][str(i)] = {
                "status": LEGADO,
                "tentativas": 1,
                "atualizado_em": cp["ultima_atualizacao"],
            }

    # Falhas fora do intervalo (não deveria ocorrer): preserva mesmo assim.
    for i, f in falhas_v1.items():
        cp["registros"].setdefault(str(i), {
            "status": FALHA,
            "cpf_cnpj": f.get("cpf_cnpj"),
            "nome": f.get("nome"),
            "tentativas": 1,
            "erro": f.get("erro"),
            "atualizado_em": cp["ultima_atualizacao"],
        })

    return cp


def carregar_checkpoint(arquivo: Path, *, fazer_backup: bool = True) -> dict:
    arquivo = Path(arquivo)

    if not arquivo.exists():
        return criar_checkpoint()

    with open(arquivo, "r", encoding="utf-8") as f:
        bruto = json.load(f)

    if bruto.get("versao") != 2 and fazer_backup:
        carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = arquivo.with_name(f"{arquivo.name}.bak-v1-{carimbo}")
        shutil.copy2(arquivo, backup)
        print(f"Backup do checkpoint v1: {backup}")

    return migrar_checkpoint(bruto)


def _falhas_pendentes(cp: dict) -> list[dict]:
    return [
        {"indice": int(i), **r}
        for i, r in sorted(
            cp["registros"].items(), key=lambda kv: int(kv[0])
        )
        if r.get("status") == FALHA
    ]


def salvar_checkpoint(cp: dict, arquivo: Path) -> None:
    """Grava o checkpoint de forma atômica."""

    arquivo = Path(arquivo)
    cp["ultima_atualizacao"] = agora()
    cp["falhas"] = _falhas_pendentes(cp)
    cp["erros"] = len(cp["falhas"])

    arquivo.parent.mkdir(parents=True, exist_ok=True)

    descritor, nome_tmp = tempfile.mkstemp(
        prefix=f".{arquivo.name}.", suffix=".tmp", dir=arquivo.parent
    )

    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as f:
            json.dump(cp, f, ensure_ascii=False, indent=2)

        os.replace(nome_tmp, arquivo)
    except BaseException:
        Path(nome_tmp).unlink(missing_ok=True)
        raise


def registrar(cp: dict, indice: int, status: str, **dados) -> None:
    anterior = cp["registros"].get(str(indice), {})
    novo = {
        "status": status,
        "tentativas": int(anterior.get("tentativas", 0)) + 1,
        "atualizado_em": agora(),
        **dados,
    }
    cp["registros"][str(indice)] = novo


# ----------------------------------------------------------------------
# Execução
# ----------------------------------------------------------------------

def _resumo_vazio() -> dict:
    return {
        "total_entrada": 0,
        "tentados": 0,
        "com_dados": 0,
        "sem_dados": 0,
        "ignorados": 0,
        "falhas": 0,
        "arquivos_gravados": 0,
        "falhas_pendentes": 0,
        "indice_retomada": 0,
        "completo": False,
        "motivo_parada": "",
    }


def _processar_favorecido(
    extractor,
    indice: int,
    row,
    cp: dict,
    empenhos_dir: Path,
    resumo: dict,
) -> bool:
    """Processa um favorecido. Devolve True se houve falha técnica."""

    cpf_cnpj, motivo = validar_cpf_cnpj(row.get("cnpj_cpf_favorecido"))
    nome, nome_ausente = normalizar_nome(row.get("nome_favorecido"))

    print()
    print("-" * 70)
    print(f"[índice {indice}] Favorecido: {nome}")

    if cpf_cnpj is None:
        print(f"Ignorado: CPF/CNPJ inválido ({motivo}).")
        registrar(
            cp, indice, IGNORADO,
            cpf_cnpj=None, nome=nome, motivo=motivo,
            nome_ausente=nome_ausente,
        )
        resumo["ignorados"] += 1
        return False

    print(f"CPF/CNPJ: {cpf_cnpj}")
    resumo["tentados"] += 1

    try:
        df = extractor.buscar_empenhos(
            ano=ANO,
            cpf_cnpj=cpf_cnpj,
            page_size=PAGE_SIZE,
            cod_orgao=COD_ORGAO,
            cod_funcao=COD_FUNCAO,
        )

        if df.empty:
            print("Nenhum empenho encontrado (consulta válida).")
            registrar(
                cp, indice, SEM_DADOS,
                cpf_cnpj=cpf_cnpj, nome=nome, quantidade=0,
            )
            resumo["sem_dados"] += 1
            return False

        # O CSV precisa pertencer ao favorecido consultado.
        if "cnpj_cpf_favorecido" in df.columns:
            devolvidos = {
                re.sub(r"\D", "", str(v))
                for v in df["cnpj_cpf_favorecido"].dropna()
            }
            if devolvidos - {cpf_cnpj}:
                raise ValueError(
                    "A API devolveu registros de outro favorecido: "
                    f"{sorted(devolvidos - {cpf_cnpj})[:3]}"
                )
        else:
            df["cnpj_cpf_favorecido"] = cpf_cnpj

        if "nome_favorecido" not in df.columns:
            df["nome_favorecido"] = nome

        arquivo = empenhos_dir / f"{cpf_cnpj}.csv"
        extractor.salvar_csv(df, arquivo)

        registrar(
            cp, indice, COM_DADOS,
            cpf_cnpj=cpf_cnpj, nome=nome, quantidade=len(df),
            arquivo=arquivo.name,
            duplicatas_removidas=int(
                df.attrs.get("duplicatas_removidas", 0)
            ),
        )
        resumo["com_dados"] += 1
        resumo["arquivos_gravados"] += 1
        return False

    except Exception as erro:  # noqa: BLE001 - registrado como falha
        print(f"ERRO ({type(erro).__name__}): {erro}")
        registrar(
            cp, indice, FALHA,
            cpf_cnpj=cpf_cnpj, nome=nome,
            tipo_erro=type(erro).__name__, erro=str(erro),
        )
        resumo["falhas"] += 1
        return True


def executar(
    df_favorecidos: pd.DataFrame,
    extractor,
    *,
    empenhos_dir: Path,
    checkpoint_file: Path,
    limite: int = LIMITE_PADRAO,
    inicio: int | None = None,
    reprocessar_falhas: bool = False,
    falhas_consecutivas_max: int = FALHAS_CONSECUTIVAS_MAX,
) -> dict:
    """
    Executa a extração e devolve o resumo. Nenhum caminho é fixo aqui,
    o que permite testar com diretórios temporários.
    """

    if limite < 1:
        raise ValueError("O limite deve ser >= 1.")

    cp = carregar_checkpoint(checkpoint_file)
    total = len(df_favorecidos)

    resumo = _resumo_vazio()
    resumo["total_entrada"] = total

    if inicio is not None:
        cp["indice"] = inicio

    empenhos_dir.mkdir(parents=True, exist_ok=True)

    if reprocessar_falhas:
        fila = [f["indice"] for f in _falhas_pendentes(cp)][:limite]
        print(f"Reprocessando {len(fila)} falha(s) pendente(s).")
    else:
        fila = list(range(cp["indice"], min(cp["indice"] + limite, total)))

    consecutivas = 0

    for indice in fila:
        if indice >= total:
            continue

        falhou = _processar_favorecido(
            extractor,
            indice,
            df_favorecidos.iloc[indice],
            cp,
            empenhos_dir,
            resumo,
        )

        if not reprocessar_falhas:
            cp["indice"] = max(cp["indice"], indice + 1)

        cp["processados"] = sum(
            1 for r in cp["registros"].values()
            if r["status"] in (COM_DADOS, SEM_DADOS, LEGADO)
        )

        salvar_checkpoint(cp, checkpoint_file)

        consecutivas = consecutivas + 1 if falhou else 0

        if consecutivas >= falhas_consecutivas_max:
            resumo["motivo_parada"] = (
                f"{consecutivas} falhas consecutivas; execução "
                "interrompida (possível indisponibilidade da API)."
            )
            break

    salvar_checkpoint(cp, checkpoint_file)

    pendentes = _falhas_pendentes(cp)
    resumo["falhas_pendentes"] = len(pendentes)
    resumo["indice_retomada"] = cp["indice"]
    resumo["completo"] = cp["indice"] >= total and not pendentes

    if not resumo["motivo_parada"]:
        if resumo["completo"]:
            resumo["motivo_parada"] = "todos os favorecidos foram processados"
        elif pendentes:
            resumo["motivo_parada"] = (
                f"{len(pendentes)} falha(s) pendente(s) de recuperação"
            )
        else:
            resumo["motivo_parada"] = "limite da execução atingido"

    return resumo


def imprimir_relatorio(resumo: dict, modo: str) -> None:
    print()
    print("=" * 70)
    print(
        "EXTRAÇÃO COMPLETA" if resumo["completo"]
        else "EXECUÇÃO PARCIAL (extração NÃO concluída)"
    )
    print("=" * 70)
    print(f"Modo:                                {modo}")
    print(f"Favorecidos na entrada:              {resumo['total_entrada']}")
    print(f"Registros tentados nesta execução:   {resumo['tentados']}")
    print(f"Consultas concluídas com dados:      {resumo['com_dados']}")
    print(f"Consultas concluídas sem dados:      {resumo['sem_dados']}")
    print(f"Ignorados por identificador inválido:{resumo['ignorados']:>4}")
    print(f"Falhas nesta execução:               {resumo['falhas']}")
    print(f"Arquivos gravados/atualizados:       {resumo['arquivos_gravados']}")
    print(f"Falhas pendentes de recuperação:     {resumo['falhas_pendentes']}")
    print(f"Índice de retomada:                  {resumo['indice_retomada']}")
    print(f"Situação: {resumo['motivo_parada']}")


def ler_argumentos(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--modo", choices=("teste", "producao"), default="teste",
        help="teste (padrão): diretório e checkpoint isolados.",
    )
    p.add_argument(
        "--limite", type=int, default=LIMITE_PADRAO,
        help=f"máximo de favorecidos por execução (padrão {LIMITE_PADRAO}).",
    )
    p.add_argument(
        "--inicio", type=int, default=None,
        help="índice inicial (somente no modo teste).",
    )
    p.add_argument(
        "--reprocessar-falhas", action="store_true",
        help="reprocessa apenas as falhas pendentes do checkpoint.",
    )
    args = p.parse_args(argv)

    if args.inicio is not None and args.modo != "teste":
        p.error("--inicio só é permitido no modo teste.")

    if args.inicio is not None and args.inicio < 0:
        p.error("--inicio deve ser >= 0.")

    if args.limite < 1:
        p.error("--limite deve ser >= 1.")

    return args


def main(argv=None) -> int:
    args = ler_argumentos(argv)

    print("=" * 70)
    print(f"EXTRAÇÃO DE EMPENHOS — modo {args.modo.upper()}")
    print("=" * 70)

    if not FAVORECIDOS_FILE.exists():
        raise FileNotFoundError(
            "Arquivo de favorecidos não encontrado: "
            f"{FAVORECIDOS_FILE}"
        )

    if args.modo == "producao":
        empenhos_dir, checkpoint_file = EMPENHOS_DIR, CHECKPOINT_FILE
    else:
        empenhos_dir = TESTE_DIR / "empenhos"
        checkpoint_file = TESTE_DIR / "checkpoints" / NOME_CHECKPOINT

    print(f"Empenhos:   {empenhos_dir}")
    print(f"Checkpoint: {checkpoint_file}")

    df_favorecidos = pd.read_csv(
        FAVORECIDOS_FILE,
        dtype={"cnpj_cpf_favorecido": str},
    )

    print(f"Favorecidos: {len(df_favorecidos)}")

    extractor = DespesasExtractor(
        timeout=60,
        max_retries=3,
        delay=0.2,
    )

    resumo = executar(
        df_favorecidos,
        extractor,
        empenhos_dir=empenhos_dir,
        checkpoint_file=checkpoint_file,
        limite=args.limite,
        inicio=args.inicio,
        reprocessar_falhas=args.reprocessar_falhas,
    )

    imprimir_relatorio(resumo, args.modo)

    return 1 if resumo["falhas"] else 0


if __name__ == "__main__":
    sys.exit(main())
