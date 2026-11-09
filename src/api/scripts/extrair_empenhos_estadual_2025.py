
from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.api.scripts.despesas_extractor import DespesasExtractor


ANO = 2025
PAGE_SIZE = 50
FALHAS_CONSECUTIVAS_MAX = 5

BASE_DIR = Path(__file__).resolve().parents[3]
RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "data" / "output"

FAVORECIDOS_FILE = RAW_DIR / "favorecidos_2025_estadual.csv"
EMPENHOS_DIR = RAW_DIR / "empenhos_estadual_2025"

CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
CHECKPOINT_FILE = CHECKPOINT_DIR / "empenhos_estadual_2025.sqlite"

ESPECIAIS_FILE = OUTPUT_DIR / "favorecidos_especiais_2025.csv"
DUPLICADOS_FILE = OUTPUT_DIR / "favorecidos_documentos_repetidos_2025.csv"


def normalizar_documento(valor):
    if pd.isna(valor):
        return None

    documento = re.sub(r"[.\-/\s]", "", str(valor).strip())

    if documento.isdigit() and len(documento) in (11, 14):
        return documento

    return None


def carregar_favorecidos():
    if not FAVORECIDOS_FILE.exists():
        raise FileNotFoundError(FAVORECIDOS_FILE)

    df = pd.read_csv(
        FAVORECIDOS_FILE,
        dtype={"cnpj_cpf_favorecido": str},
        encoding="utf-8-sig",
    )

    if "cnpj_cpf_favorecido" not in df.columns:
        raise ValueError("Coluna cnpj_cpf_favorecido não encontrada.")

    df["documento_normalizado"] = (
        df["cnpj_cpf_favorecido"].apply(normalizar_documento)
    )

    validos = df[df["documento_normalizado"].notna()].copy()
    especiais = df[df["documento_normalizado"].isna()].copy()

    duplicados = validos[
        validos.duplicated(
            subset=["documento_normalizado"],
            keep=False,
        )
    ].copy()

    # Uma consulta por documento. Mantém a primeira ocorrência
    # e registra as repetições em arquivo separado.
    unicos = validos.drop_duplicates(
        subset=["documento_normalizado"],
        keep="first",
    ).copy()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    especiais.to_csv(
        ESPECIAIS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    if not duplicados.empty:
        duplicados.to_csv(
            DUPLICADOS_FILE,
            index=False,
            encoding="utf-8-sig",
        )

    print("\n========== ENTRADA ==========")
    print(f"Registros originais: {len(df)}")
    print(f"Documentos numéricos: {len(validos)}")
    print(f"Documentos numéricos únicos: {len(unicos)}")
    print(f"Documentos repetidos: {len(duplicados)}")
    print(f"Identificadores especiais: {len(especiais)}")
    print(f"Arquivo de especiais: {ESPECIAIS_FILE}")

    return unicos.reset_index(drop=True)


def inicializar_checkpoint():
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(CHECKPOINT_FILE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS favorecidos (
            documento TEXT PRIMARY KEY,
            nome TEXT,
            status TEXT NOT NULL DEFAULT 'pendente',
            quantidade INTEGER DEFAULT 0,
            erro TEXT,
            atualizado_em TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadados (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)

    # Impede reutilizar um checkpoint com outro CSV de entrada.
    hash_arquivo = hashlib.sha256(
        FAVORECIDOS_FILE.read_bytes()
    ).hexdigest()

    anterior = conn.execute(
        "SELECT valor FROM metadados WHERE chave = 'hash_entrada'"
    ).fetchone()

    if anterior and anterior[0] != hash_arquivo:
        conn.close()
        raise RuntimeError(
            "O CSV de favorecidos foi alterado desde a criação "
            "do checkpoint. Não reutilize esse checkpoint com "
            "uma entrada diferente."
        )

    conn.execute(
        "INSERT OR IGNORE INTO metadados (chave, valor) VALUES (?, ?)",
        ("hash_entrada", hash_arquivo),
    )

    conn.commit()
    return conn


def registrar(conn, documento, nome, status, quantidade=0, erro=None):
    conn.execute("""
        INSERT INTO favorecidos (
            documento, nome, status, quantidade, erro, atualizado_em
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(documento) DO UPDATE SET
            nome = excluded.nome,
            status = excluded.status,
            quantidade = excluded.quantidade,
            erro = excluded.erro,
            atualizado_em = excluded.atualizado_em
    """, (
        documento,
        nome,
        status,
        quantidade,
        erro,
        datetime.now().isoformat(timespec="seconds"),
    ))

    conn.commit()


def processar_favorecido(extractor, conn, row):
    documento = row["documento_normalizado"]
    nome = str(row.get("nome_favorecido", "Não informado"))

    print(f"\nFavorecido: {nome}")
    print(f"Documento: {documento}")

    try:
        df = extractor.buscar_empenhos(
            ano=ANO,
            cpf_cnpj=documento,
            page_size=PAGE_SIZE,
            # Sem filtro de órgão ou função.
        )

        if df.empty:
            registrar(
                conn, documento, nome, "sem_dados"
            )
            return "sem_dados"

        if "cnpj_cpf_favorecido" in df.columns:
            documentos_devolvidos = (
                df["cnpj_cpf_favorecido"].apply(normalizar_documento)
            )

            if documentos_devolvidos.isna().any():
                raise ValueError(
                    "A API devolveu linhas sem CPF/CNPJ válido."
                )

            devolvidos = set(documentos_devolvidos)

            if devolvidos != {documento}:
                raise ValueError(
                    "A API devolveu documentos diferentes do consultado: "
                    f"{sorted(devolvidos)[:5]}"
                )
        else:
            df["cnpj_cpf_favorecido"] = documento

        if "nome_favorecido" not in df.columns:
            df["nome_favorecido"] = nome

        pasta = EMPENHOS_DIR / documento[:3]
        arquivo = pasta / f"{documento}.csv"

        extractor.salvar_csv(df, arquivo)

        registrar(
            conn,
            documento,
            nome,
            "com_dados",
            quantidade=len(df),
        )

        print(f"Empenhos encontrados: {len(df)}")
        print(f"Arquivo: {arquivo}")

        return "com_dados"

    except Exception as erro:
        registrar(
            conn,
            documento,
            nome,
            "falha",
            erro=f"{type(erro).__name__}: {erro}",
        )

        print(f"ERRO: {type(erro).__name__}: {erro}")

        return "falha"


def imprimir_resumo(conn):
    print("\n========== RESUMO DO CHECKPOINT ==========")

    resultados = conn.execute("""
        SELECT status, COUNT(*), COALESCE(SUM(quantidade), 0)
        FROM favorecidos
        GROUP BY status
        ORDER BY status
    """).fetchall()

    for status, quantidade, linhas in resultados:
        print(
            f"{status}: {quantidade} favorecidos | "
            f"{linhas} linhas de empenho"
        )

    total = conn.execute(
        "SELECT COUNT(*) FROM favorecidos"
    ).fetchone()[0]

    concluidos = conn.execute("""
        SELECT COUNT(*)
        FROM favorecidos
        WHERE status IN ('com_dados', 'sem_dados')
    """).fetchone()[0]

    falhas = conn.execute("""
        SELECT COUNT(*)
        FROM favorecidos
        WHERE status = 'falha'
    """).fetchone()[0]

    print(f"\nTotal registrado: {total}")
    print(f"Concluídos: {concluidos}")
    print(f"Falhas pendentes: {falhas}")
    print(f"Checkpoint: {CHECKPOINT_FILE}")


def executar(limite=None, reprocessar_falhas=False):
    df = carregar_favorecidos()
    conn = inicializar_checkpoint()

    try:
        # Registra todos os documentos como pendentes, sem sobrescrever
        # estados já existentes no checkpoint.
        conn.executemany("""
            INSERT OR IGNORE INTO favorecidos (
                documento, nome, status, quantidade
            )
            VALUES (?, ?, 'pendente', 0)
        """, [
            (
                row["documento_normalizado"],
                str(row.get("nome_favorecido", "Não informado")),
            )
            for _, row in df.iterrows()
        ])
        conn.commit()

        extractor = DespesasExtractor(
            timeout=60,
            max_retries=3,
            delay=0.2,
        )

        processados_execucao = 0
        falhas_consecutivas = 0

        total = len(df)

        print("\n========== INÍCIO DA EXTRAÇÃO ESTADUAL ==========")
        print(f"Ano: {ANO}")
        print(f"Favorecidos únicos: {total}")
        print(f"Page size: {PAGE_SIZE}")
        print(f"Limite desta execução: {limite or 'todos os pendentes'}")
        print(f"Diretório: {EMPENHOS_DIR}")

        for indice, (_, row) in enumerate(df.iterrows(), start=1):
            documento = row["documento_normalizado"]

            atual = conn.execute(
                "SELECT status FROM favorecidos WHERE documento = ?",
                (documento,),
            ).fetchone()

            status_atual = atual[0] if atual else "pendente"

            if reprocessar_falhas:
                if status_atual != "falha":
                    continue
            else:
                if status_atual != "pendente":
                    continue

            if limite is not None and processados_execucao >= limite:
                break

            status = processar_favorecido(
                extractor,
                conn,
                row,
            )

            processados_execucao += 1

            if status == "falha":
                falhas_consecutivas += 1
            else:
                falhas_consecutivas = 0

            if processados_execucao % 25 == 0:
                print(
                    f"\nProgresso desta execução: "
                    f"{processados_execucao} consultas"
                )
                imprimir_resumo(conn)

            if falhas_consecutivas >= FALHAS_CONSECUTIVAS_MAX:
                print(
                    "\nExecução interrompida por "
                    f"{falhas_consecutivas} falhas consecutivas."
                )
                print("Verifique a disponibilidade da API antes de retomar.")
                break

        imprimir_resumo(conn)

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Extração estadual de empenhos de 2025."
    )

    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Quantidade máxima de favorecidos nesta execução.",
    )

    parser.add_argument(
        "--reprocessar-falhas",
        action="store_true",
        help="Consulta novamente apenas os favorecidos com falha.",
    )

    args = parser.parse_args()

    if args.limite is not None and args.limite < 1:
        parser.error("--limite deve ser maior que zero.")

    executar(
        limite=args.limite,
        reprocessar_falhas=args.reprocessar_falhas,
    )


if __name__ == "__main__":
    main()
