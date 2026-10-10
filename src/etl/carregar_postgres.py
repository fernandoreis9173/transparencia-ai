from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from psycopg.rows import dict_row

# Permite executar:
# python src/etl/carregar_postgres.py
ROOT_DIR = Path(__file__).resolve().parents[2]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.db.connection import get_connection


# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

PARQUET_FILE = (
    ROOT_DIR
    / "data"
    / "processed"
    / "empenhos_2025_orgao_48000_funcao_12.parquet"
)

FONTE_CODIGO = "GOVERNO_ESTADO_SP"


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def valor_nulo(valor):
    """
    Converte NaN/NaT/NA do Pandas para None.

    O PostgreSQL receberá None como NULL.
    """
    if pd.isna(valor):
        return None

    return valor


def codigo_inteiro(valor):
    """
    Converte códigos numéricos para int.

    Valores nulos são convertidos para None.
    """
    if pd.isna(valor):
        return None

    return int(valor)


def codigo_texto(valor):
    """
    Converte códigos para texto.

    Mantém NULL como None e evita situações como:
        123.0 -> '123'
        NaN   -> None
    """
    if pd.isna(valor):
        return None

    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))

    return str(valor)


# =============================================================================
# CARREGAR PARQUET
# =============================================================================

def carregar_parquet() -> pd.DataFrame:
    print("=" * 80)
    print("📦 CARREGANDO PARQUET")
    print("=" * 80)

    if not PARQUET_FILE.exists():
        raise FileNotFoundError(
            f"Parquet não encontrado: {PARQUET_FILE}"
        )

    df = pd.read_parquet(PARQUET_FILE)

    print(f"Arquivo: {PARQUET_FILE}")
    print(f"Registros: {len(df):,}")
    print(f"Colunas: {len(df.columns)}")

    return df


# =============================================================================
# NORMALIZAÇÃO
# =============================================================================

def normalizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    print()
    print("=" * 80)
    print("🧹 NORMALIZANDO DATAFRAME")
    print("=" * 80)

    df = df.copy()

    # -------------------------------------------------------------------------
    # Campos textuais
    # -------------------------------------------------------------------------

    campos_texto = [
        "cnpj_cpf_favorecido",
        "nome_favorecido",
        "nome_orgao",
        "nome_uo",
        "nome_ug",
        "nome_funcao",
        "nome_subfuncao",
        "nome_programa",
        "nome_acao",
        "nome_elemento",
        "nome_categoria_despesa",
        "nome_grupo",
        "nome_modalidade_aplicacao",
        "nome_item",
        "nome_fonte",
        "num_processo",
        "indicador_restos",
        "num_empenho",
    ]

    for coluna in campos_texto:
        if coluna in df.columns:
            df[coluna] = df[coluna].astype("string")

    # -------------------------------------------------------------------------
    # Valores numéricos
    # -------------------------------------------------------------------------

    campos_numericos = [
        "ano_exercicio",
        "cod_orgao",
        "cod_uo",
        "cod_funcao",
        "cod_subfuncao",
        "cod_programa",
        "cod_acao",
        "cod_elemento",
        "cod_ug",
        "cod_categoria_despesa",
        "cod_grupo",
        "cod_modalidade_aplicacao",
        "cod_item",
        "cod_fonte",
        "cod_fonte_detalhada",
        "cod_tipo_licitacao",
        "vl_empenhado",
        "vl_liquidado",
        "vl_pago",
        "vl_pago_rp",
        "vl_dotacao_atual",
        "vl_empenhado_inicial",
        "vl_reforco",
        "vl_anulacao",
    ]

    for coluna in campos_numericos:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(
                df[coluna],
                errors="coerce",
            )

    # -------------------------------------------------------------------------
    # Data
    # -------------------------------------------------------------------------

    if "data_registro_empenho" in df.columns:
        df["data_registro_empenho"] = pd.to_datetime(
            df["data_registro_empenho"],
            errors="coerce",
        )

    # -------------------------------------------------------------------------
    # NaN / NaT / pd.NA -> None
    # -------------------------------------------------------------------------

    df = df.astype(object).where(pd.notna(df), None)

    return df


# =============================================================================
# BUSCAR FONTE
# =============================================================================

def buscar_fonte(conn):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id
            FROM core.fonte
            WHERE codigo = %s
            """,
            (FONTE_CODIGO,),
        )

        fonte = cur.fetchone()

    if not fonte:
        raise RuntimeError(
            f"Fonte '{FONTE_CODIGO}' não cadastrada."
        )

    return fonte["id"]


# =============================================================================
# INSERIR DIMENSÕES
# =============================================================================

def inserir_dimensoes(
    conn,
    df: pd.DataFrame,
    fonte_id: int,
):
    print()
    print("=" * 80)
    print("🏗️ INSERINDO DIMENSÕES")
    print("=" * 80)

    with conn.cursor() as cur:

        # ---------------------------------------------------------------------
        # ÓRGÃOS
        # ---------------------------------------------------------------------

        orgaos = (
            df[
                ["cod_orgao", "nome_orgao"]
            ]
            .drop_duplicates()
            .dropna(
                subset=[
                    "cod_orgao",
                    "nome_orgao",
                ]
            )
        )

        for row in orgaos.itertuples(index=False):

            cur.execute(
                """
                INSERT INTO core.orgao
                    (
                        fonte_id,
                        codigo,
                        nome
                    )
                VALUES
                    (%s, %s, %s)
                ON CONFLICT (fonte_id, codigo)
                DO UPDATE SET
                    nome = EXCLUDED.nome
                """,
                (
                    fonte_id,
                    codigo_texto(row.cod_orgao),
                    row.nome_orgao,
                ),
            )

        print(f"Órgãos: {len(orgaos)}")

        # ---------------------------------------------------------------------
        # UNIDADES ORÇAMENTÁRIAS
        # ---------------------------------------------------------------------

        uos = (
            df[
                ["cod_uo", "nome_uo"]
            ]
            .drop_duplicates()
            .dropna(
                subset=[
                    "cod_uo",
                    "nome_uo",
                ]
            )
        )

        for row in uos.itertuples(index=False):

            cur.execute(
                """
                INSERT INTO core.unidade_orcamentaria
                    (
                        fonte_id,
                        codigo,
                        nome
                    )
                VALUES
                    (%s, %s, %s)
                ON CONFLICT (fonte_id, codigo)
                DO UPDATE SET
                    nome = EXCLUDED.nome
                """,
                (
                    fonte_id,
                    codigo_texto(row.cod_uo),
                    row.nome_uo,
                ),
            )

        print(f"UOs: {len(uos)}")

        # ---------------------------------------------------------------------
        # UNIDADES GESTORAS
        # ---------------------------------------------------------------------

        ugs = (
            df[
                ["cod_ug", "nome_ug"]
            ]
            .drop_duplicates()
            .dropna(
                subset=[
                    "cod_ug",
                ]
            )
        )

        for row in ugs.itertuples(index=False):

            cur.execute(
                """
                INSERT INTO core.unidade_gestora
                    (
                        fonte_id,
                        codigo,
                        nome
                    )
                VALUES
                    (%s, %s, %s)
                ON CONFLICT (fonte_id, codigo)
                DO UPDATE SET
                    nome = EXCLUDED.nome
                """,
                (
                    fonte_id,
                    codigo_texto(row.cod_ug),
                    valor_nulo(row.nome_ug),
                ),
            )

        print(f"UGs: {len(ugs)}")

        # ---------------------------------------------------------------------
        # FAVORECIDOS
        # ---------------------------------------------------------------------

        favorecidos = (
            df[
                [
                    "cnpj_cpf_favorecido",
                    "nome_favorecido",
                ]
            ]
            .drop_duplicates()
            .dropna(
                subset=[
                    "cnpj_cpf_favorecido",
                    "nome_favorecido",
                ]
            )
        )

        for row in favorecidos.itertuples(index=False):

            documento = (
                str(row.cnpj_cpf_favorecido)
                .strip()
            )

            tipo_pessoa = None

            if len(documento) == 11:
                tipo_pessoa = "PF"

            elif len(documento) == 14:
                tipo_pessoa = "PJ"

            cur.execute(
                """
                INSERT INTO core.favorecido
                    (
                        fonte_id,
                        documento,
                        nome,
                        tipo_pessoa
                    )
                VALUES
                    (%s, %s, %s, %s)
                ON CONFLICT (fonte_id, documento)
                DO UPDATE SET
                    nome = EXCLUDED.nome,
                    tipo_pessoa = EXCLUDED.tipo_pessoa,
                    atualizado_em = CURRENT_TIMESTAMP
                """,
                (
                    fonte_id,
                    documento,
                    row.nome_favorecido,
                    tipo_pessoa,
                ),
            )

        print(f"Favorecidos: {len(favorecidos)}")

        # ---------------------------------------------------------------------
        # FUNÇÕES
        # ---------------------------------------------------------------------

        funcoes = (
            df[
                [
                    "cod_funcao",
                    "nome_funcao",
                ]
            ]
            .drop_duplicates()
            .dropna(
                subset=[
                    "cod_funcao",
                    "nome_funcao",
                ]
            )
        )

        for row in funcoes.itertuples(index=False):

            cur.execute(
                """
                INSERT INTO core.funcao
                    (
                        fonte_id,
                        codigo,
                        nome
                    )
                VALUES
                    (%s, %s, %s)
                ON CONFLICT (fonte_id, codigo)
                DO UPDATE SET
                    nome = EXCLUDED.nome
                """,
                (
                    fonte_id,
                    codigo_texto(row.cod_funcao),
                    row.nome_funcao,
                ),
            )

        print(f"Funções: {len(funcoes)}")

        # ---------------------------------------------------------------------
        # SUBFUNÇÕES
        # ---------------------------------------------------------------------

        subfuncoes = (
            df[
                [
                    "cod_subfuncao",
                    "nome_subfuncao",
                ]
            ]
            .drop_duplicates()
            .dropna(
                subset=[
                    "cod_subfuncao",
                    "nome_subfuncao",
                ]
            )
        )

        for row in subfuncoes.itertuples(index=False):

            cur.execute(
                """
                INSERT INTO core.subfuncao
                    (
                        fonte_id,
                        codigo,
                        nome
                    )
                VALUES
                    (%s, %s, %s)
                ON CONFLICT (fonte_id, codigo)
                DO UPDATE SET
                    nome = EXCLUDED.nome
                """,
                (
                    fonte_id,
                    codigo_texto(row.cod_subfuncao),
                    row.nome_subfuncao,
                ),
            )

        print(f"Subfunções: {len(subfuncoes)}")

        # ---------------------------------------------------------------------
        # PROGRAMAS
        # ---------------------------------------------------------------------

        programas = (
            df[
                [
                    "cod_programa",
                    "nome_programa",
                ]
            ]
            .drop_duplicates()
            .dropna(
                subset=[
                    "cod_programa",
                    "nome_programa",
                ]
            )
        )

        for row in programas.itertuples(index=False):

            cur.execute(
                """
                INSERT INTO core.programa
                    (
                        fonte_id,
                        codigo,
                        nome
                    )
                VALUES
                    (%s, %s, %s)
                ON CONFLICT (fonte_id, codigo)
                DO UPDATE SET
                    nome = EXCLUDED.nome
                """,
                (
                    fonte_id,
                    codigo_texto(row.cod_programa),
                    row.nome_programa,
                ),
            )

        print(f"Programas: {len(programas)}")

        # ---------------------------------------------------------------------
        # AÇÕES
        # ---------------------------------------------------------------------

        acoes = (
            df[
                [
                    "cod_acao",
                    "nome_acao",
                ]
            ]
            .drop_duplicates()
            .dropna(
                subset=[
                    "cod_acao",
                    "nome_acao",
                ]
            )
        )

        for row in acoes.itertuples(index=False):

            cur.execute(
                """
                INSERT INTO core.acao
                    (
                        fonte_id,
                        codigo,
                        nome
                    )
                VALUES
                    (%s, %s, %s)
                ON CONFLICT (fonte_id, codigo)
                DO UPDATE SET
                    nome = EXCLUDED.nome
                """,
                (
                    fonte_id,
                    codigo_texto(row.cod_acao),
                    row.nome_acao,
                ),
            )

        print(f"Ações: {len(acoes)}")

        # ---------------------------------------------------------------------
        # TIPOS DE LICITAÇÃO
        # ---------------------------------------------------------------------

        tipos = (
            df[
                [
                    "cod_tipo_licitacao",
                    "nome_tipo_licitacao",
                ]
            ]
            .drop_duplicates()
            .dropna(
                subset=[
                    "cod_tipo_licitacao",
                ]
            )
        )

        for row in tipos.itertuples(index=False):

            nome = valor_nulo(
                row.nome_tipo_licitacao
            )

            if nome is None:
                nome = str(
                    row.cod_tipo_licitacao
                )

            cur.execute(
                """
                INSERT INTO core.tipo_licitacao
                    (
                        codigo,
                        nome
                    )
                VALUES
                    (%s, %s)
                ON CONFLICT (codigo)
                DO UPDATE SET
                    nome = EXCLUDED.nome
                """,
                (
                    codigo_texto(
                        row.cod_tipo_licitacao
                    ),
                    nome,
                ),
            )

        print(
            f"Tipos de licitação: {len(tipos)}"
        )


# =============================================================================
# INSERIR FATOS
# =============================================================================

def inserir_fatos(
    conn,
    df: pd.DataFrame,
    fonte_id: int,
):
    print()
    print("=" * 80)
    print("💰 INSERINDO FATOS DE DESPESA")
    print("=" * 80)

    with conn.cursor(row_factory=dict_row) as cur:

        total = len(df)

        for index, row in enumerate(
            df.itertuples(index=False),
            start=1,
        ):

            try:

                # -------------------------------------------------------------
                # Função auxiliar para buscar IDs
                # -------------------------------------------------------------

                def buscar_id(sql, params):

                    cur.execute(
                        sql,
                        params,
                    )

                    resultado = cur.fetchone()

                    return (
                        resultado["id"]
                        if resultado
                        else None
                    )

                # -------------------------------------------------------------
                # IDs DAS DIMENSÕES
                # -------------------------------------------------------------

                orgao_id = buscar_id(
                    """
                    SELECT id
                    FROM core.orgao
                    WHERE fonte_id = %s
                      AND codigo = %s
                    """,
                    (
                        fonte_id,
                        codigo_texto(
                            row.cod_orgao
                        ),
                    ),
                )

                uo_id = buscar_id(
                    """
                    SELECT id
                    FROM core.unidade_orcamentaria
                    WHERE fonte_id = %s
                      AND codigo = %s
                    """,
                    (
                        fonte_id,
                        codigo_texto(
                            row.cod_uo
                        ),
                    ),
                )

                # -------------------------------------------------------------
                # UNIDADE GESTORA
                # -------------------------------------------------------------

                ug_id = None

                if pd.notna(row.cod_ug):

                    ug_id = buscar_id(
                        """
                        SELECT id
                        FROM core.unidade_gestora
                        WHERE fonte_id = %s
                          AND codigo = %s
                        """,
                        (
                            fonte_id,
                            codigo_texto(
                                row.cod_ug
                            ),
                        ),
                    )

                # -------------------------------------------------------------
                # FAVORECIDO
                # -------------------------------------------------------------

                favorecido_id = buscar_id(
                    """
                    SELECT id
                    FROM core.favorecido
                    WHERE fonte_id = %s
                      AND documento = %s
                    """,
                    (
                        fonte_id,
                        codigo_texto(
                            row.cnpj_cpf_favorecido
                        ),
                    ),
                )

                # -------------------------------------------------------------
                # FUNÇÃO
                # -------------------------------------------------------------

                funcao_id = buscar_id(
                    """
                    SELECT id
                    FROM core.funcao
                    WHERE fonte_id = %s
                      AND codigo = %s
                    """,
                    (
                        fonte_id,
                        codigo_texto(
                            row.cod_funcao
                        ),
                    ),
                )

                # -------------------------------------------------------------
                # SUBFUNÇÃO
                # -------------------------------------------------------------

                subfuncao_id = buscar_id(
                    """
                    SELECT id
                    FROM core.subfuncao
                    WHERE fonte_id = %s
                      AND codigo = %s
                    """,
                    (
                        fonte_id,
                        codigo_texto(
                            row.cod_subfuncao
                        ),
                    ),
                )

                # -------------------------------------------------------------
                # PROGRAMA
                # -------------------------------------------------------------

                programa_id = buscar_id(
                    """
                    SELECT id
                    FROM core.programa
                    WHERE fonte_id = %s
                      AND codigo = %s
                    """,
                    (
                        fonte_id,
                        codigo_texto(
                            row.cod_programa
                        ),
                    ),
                )

                # -------------------------------------------------------------
                # AÇÃO
                # -------------------------------------------------------------

                acao_id = buscar_id(
                    """
                    SELECT id
                    FROM core.acao
                    WHERE fonte_id = %s
                      AND codigo = %s
                    """,
                    (
                        fonte_id,
                        codigo_texto(
                            row.cod_acao
                        ),
                    ),
                )

                # -------------------------------------------------------------
                # TIPO DE LICITAÇÃO
                # -------------------------------------------------------------

                tipo_licitacao_id = buscar_id(
                    """
                    SELECT id
                    FROM core.tipo_licitacao
                    WHERE codigo = %s
                    """,
                    (
                        codigo_texto(
                            row.cod_tipo_licitacao
                        ),
                    ),
                )

                # -------------------------------------------------------------
                # CÓDIGOS DA DESPESA
                # -------------------------------------------------------------

                cod_elemento = codigo_inteiro(
                    row.cod_elemento
                )

                cod_categoria_despesa = codigo_inteiro(
                    row.cod_categoria_despesa
                )

                cod_grupo = codigo_inteiro(
                    row.cod_grupo
                )

                cod_modalidade_aplicacao = codigo_inteiro(
                    row.cod_modalidade_aplicacao
                )

                cod_item = codigo_inteiro(
                    row.cod_item
                )

                cod_fonte = codigo_inteiro(
                    row.cod_fonte
                )

                cod_fonte_detalhada = codigo_inteiro(
                    row.cod_fonte_detalhada
                )

                # -------------------------------------------------------------
                # VALORES FINANCEIROS
                # -------------------------------------------------------------

                vl_empenhado_inicial = valor_nulo(
                    row.vl_empenhado_inicial
                )

                vl_empenhado = valor_nulo(
                    row.vl_empenhado
                )

                vl_reforco = valor_nulo(
                    row.vl_reforco
                )

                vl_anulacao = valor_nulo(
                    row.vl_anulacao
                )

                vl_liquidado = valor_nulo(
                    row.vl_liquidado
                )

                vl_pago = valor_nulo(
                    row.vl_pago
                )

                vl_pago_rp = valor_nulo(
                    row.vl_pago_rp
                )

                vl_dotacao_atual = valor_nulo(
                    row.vl_dotacao_atual
                )

                # -------------------------------------------------------------
                # INSERT / UPSERT
                # -------------------------------------------------------------

                cur.execute(
                    """
                    INSERT INTO core.fato_despesa
                    (
                        fonte_id,
                        ano_exercicio,

                        orgao_id,
                        unidade_orcamentaria_id,
                        unidade_gestora_id,

                        favorecido_id,

                        funcao_id,
                        subfuncao_id,
                        programa_id,
                        acao_id,

                        tipo_licitacao_id,

                        cod_elemento,
                        cod_categoria_despesa,
                        cod_grupo,
                        cod_modalidade_aplicacao,
                        cod_item,
                        cod_fonte,
                        cod_fonte_detalhada,

                        num_empenho,
                        num_processo,

                        data_registro_empenho,

                        indicador_restos,

                        vl_empenhado_inicial,
                        vl_empenhado,
                        vl_reforco,
                        vl_anulacao,

                        vl_liquidado,
                        vl_pago,
                        vl_pago_rp,

                        vl_dotacao_atual
                    )
                    VALUES
                    (
                        %s, %s,

                        %s, %s, %s,

                        %s,

                        %s, %s, %s, %s,

                        %s,

                        %s, %s, %s, %s,
                        %s, %s, %s,

                        %s, %s,

                        %s,

                        %s,

                        %s, %s, %s, %s,

                        %s, %s, %s,

                        %s
                    )

                    ON CONFLICT (fonte_id, num_empenho)
                    DO UPDATE SET

                        ano_exercicio =
                            EXCLUDED.ano_exercicio,

                        orgao_id =
                            EXCLUDED.orgao_id,

                        unidade_orcamentaria_id =
                            EXCLUDED.unidade_orcamentaria_id,

                        unidade_gestora_id =
                            EXCLUDED.unidade_gestora_id,

                        favorecido_id =
                            EXCLUDED.favorecido_id,

                        funcao_id =
                            EXCLUDED.funcao_id,

                        subfuncao_id =
                            EXCLUDED.subfuncao_id,

                        programa_id =
                            EXCLUDED.programa_id,

                        acao_id =
                            EXCLUDED.acao_id,

                        tipo_licitacao_id =
                            EXCLUDED.tipo_licitacao_id,

                        cod_elemento =
                            EXCLUDED.cod_elemento,

                        cod_categoria_despesa =
                            EXCLUDED.cod_categoria_despesa,

                        cod_grupo =
                            EXCLUDED.cod_grupo,

                        cod_modalidade_aplicacao =
                            EXCLUDED.cod_modalidade_aplicacao,

                        cod_item =
                            EXCLUDED.cod_item,

                        cod_fonte =
                            EXCLUDED.cod_fonte,

                        cod_fonte_detalhada =
                            EXCLUDED.cod_fonte_detalhada,

                        num_processo =
                            EXCLUDED.num_processo,

                        data_registro_empenho =
                            EXCLUDED.data_registro_empenho,

                        indicador_restos =
                            EXCLUDED.indicador_restos,

                        vl_empenhado_inicial =
                            EXCLUDED.vl_empenhado_inicial,

                        vl_empenhado =
                            EXCLUDED.vl_empenhado,

                        vl_reforco =
                            EXCLUDED.vl_reforco,

                        vl_anulacao =
                            EXCLUDED.vl_anulacao,

                        vl_liquidado =
                            EXCLUDED.vl_liquidado,

                        vl_pago =
                            EXCLUDED.vl_pago,

                        vl_pago_rp =
                            EXCLUDED.vl_pago_rp,

                        vl_dotacao_atual =
                            EXCLUDED.vl_dotacao_atual,

                        atualizado_em =
                            CURRENT_TIMESTAMP
                    """,
                    (
                        fonte_id,
                        row.ano_exercicio,

                        orgao_id,
                        uo_id,
                        ug_id,

                        favorecido_id,

                        funcao_id,
                        subfuncao_id,
                        programa_id,
                        acao_id,

                        tipo_licitacao_id,

                        cod_elemento,
                        cod_categoria_despesa,
                        cod_grupo,
                        cod_modalidade_aplicacao,
                        cod_item,
                        cod_fonte,
                        cod_fonte_detalhada,

                        row.num_empenho,
                        row.num_processo,

                        row.data_registro_empenho,

                        row.indicador_restos,

                        vl_empenhado_inicial,
                        vl_empenhado,
                        vl_reforco,
                        vl_anulacao,

                        vl_liquidado,
                        vl_pago,
                        vl_pago_rp,

                        vl_dotacao_atual,
                    ),
                )

                # -------------------------------------------------------------
                # PROGRESSO
                # -------------------------------------------------------------

                if index % 100 == 0 or index == total:

                    print(
                        f"   {index:,}/{total:,} "
                        f"({index / total * 100:.1f}%)"
                    )

            except Exception as e:

                print()
                print("=" * 80)
                print("❌ ERRO AO INSERIR FATO")
                print("=" * 80)

                print(
                    f"Registro: {index}/{total}"
                )

                print(
                    f"Empenho: {row.num_empenho}"
                )

                print(
                    f"Favorecido: "
                    f"{row.nome_favorecido}"
                )

                print(
                    f"CNPJ/CPF: "
                    f"{row.cnpj_cpf_favorecido}"
                )

                print(
                    f"Erro: {e}"
                )

                print()
                print("Valores dos códigos:")

                print(
                    f"   cod_elemento: "
                    f"{cod_elemento}"
                )

                print(
                    f"   cod_categoria_despesa: "
                    f"{cod_categoria_despesa}"
                )

                print(
                    f"   cod_grupo: "
                    f"{cod_grupo}"
                )

                print(
                    f"   cod_modalidade_aplicacao: "
                    f"{cod_modalidade_aplicacao}"
                )

                print(
                    f"   cod_item: "
                    f"{cod_item}"
                )

                print(
                    f"   cod_fonte: "
                    f"{cod_fonte}"
                )

                print(
                    f"   cod_fonte_detalhada: "
                    f"{cod_fonte_detalhada}"
                )

                print()
                print("Valores financeiros:")

                print(
                    f"   vl_empenhado_inicial: "
                    f"{vl_empenhado_inicial}"
                )

                print(
                    f"   vl_empenhado: "
                    f"{vl_empenhado}"
                )

                print(
                    f"   vl_reforco: "
                    f"{vl_reforco}"
                )

                print(
                    f"   vl_anulacao: "
                    f"{vl_anulacao}"
                )

                print(
                    f"   vl_liquidado: "
                    f"{vl_liquidado}"
                )

                print(
                    f"   vl_pago: "
                    f"{vl_pago}"
                )

                print(
                    f"   vl_pago_rp: "
                    f"{vl_pago_rp}"
                )

                print(
                    f"   vl_dotacao_atual: "
                    f"{vl_dotacao_atual}"
                )

                raise


# =============================================================================
# VALIDAÇÃO
# =============================================================================

def validar_banco(conn):

    print()
    print("=" * 80)
    print("🔎 VALIDANDO BANCO")
    print("=" * 80)

    with conn.cursor() as cur:

        # ---------------------------------------------------------------------
        # Total de fatos
        # ---------------------------------------------------------------------

        cur.execute(
            """
            SELECT COUNT(*)
            FROM core.fato_despesa
            """
        )

        total = cur.fetchone()[0]

        print(
            f"Total de despesas: {total:,}"
        )

        # ---------------------------------------------------------------------
        # Total da fonte
        # ---------------------------------------------------------------------

        cur.execute(
            """
            SELECT COUNT(*)
            FROM core.fato_despesa
            WHERE fonte_id = (
                SELECT id
                FROM core.fonte
                WHERE codigo = %s
            )
            """,
            (FONTE_CODIGO,),
        )

        total_fonte = cur.fetchone()[0]

        print(
            f"Despesas Governo SP: "
            f"{total_fonte:,}"
        )

        # ---------------------------------------------------------------------
        # Totais financeiros
        # ---------------------------------------------------------------------

        cur.execute(
            """
            SELECT
                SUM(vl_empenhado),
                SUM(vl_liquidado),
                SUM(vl_pago)
            FROM core.fato_despesa
            WHERE fonte_id = (
                SELECT id
                FROM core.fonte
                WHERE codigo = %s
            )
            """,
            (FONTE_CODIGO,),
        )

        empenhado, liquidado, pago = cur.fetchone()

        print()
        print("Totais:")

        print(
            f"   Empenhado : "
            f"R$ {empenhado or 0:,.2f}"
        )

        print(
            f"   Liquidado : "
            f"R$ {liquidado or 0:,.2f}"
        )

        print(
            f"   Pago      : "
            f"R$ {pago or 0:,.2f}"
        )

        # ---------------------------------------------------------------------
        # Anomalias
        # ---------------------------------------------------------------------

        cur.execute(
            """
            SELECT COUNT(*)
            FROM core.fato_despesa
            WHERE liquidado_maior_que_empenhado = TRUE
            """
        )

        anomalias = cur.fetchone()[0]

        print()
        print(
            f"Liquidado > Empenhado: "
            f"{anomalias:,}"
        )

        # ---------------------------------------------------------------------
        # Dimensões
        # ---------------------------------------------------------------------

        print()
        print("Dimensões:")

        cur.execute(
            """
            SELECT COUNT(*)
            FROM core.orgao
            """
        )

        print(
            f"   Órgãos: "
            f"{cur.fetchone()[0]:,}"
        )

        cur.execute(
            """
            SELECT COUNT(*)
            FROM core.unidade_orcamentaria
            """
        )

        print(
            f"   UOs: "
            f"{cur.fetchone()[0]:,}"
        )

        cur.execute(
            """
            SELECT COUNT(*)
            FROM core.favorecido
            """
        )

        print(
            f"   Favorecidos: "
            f"{cur.fetchone()[0]:,}"
        )

        cur.execute(
            """
            SELECT COUNT(*)
            FROM core.funcao
            """
        )

        print(
            f"   Funções: "
            f"{cur.fetchone()[0]:,}"
        )

        cur.execute(
            """
            SELECT COUNT(*)
            FROM core.subfuncao
            """
        )

        print(
            f"   Subfunções: "
            f"{cur.fetchone()[0]:,}"
        )

        cur.execute(
            """
            SELECT COUNT(*)
            FROM core.programa
            """
        )

        print(
            f"   Programas: "
            f"{cur.fetchone()[0]:,}"
        )

        cur.execute(
            """
            SELECT COUNT(*)
            FROM core.acao
            """
        )

        print(
            f"   Ações: "
            f"{cur.fetchone()[0]:,}"
        )

        cur.execute(
            """
            SELECT COUNT(*)
            FROM core.tipo_licitacao
            """
        )

        print(
            f"   Tipos de licitação: "
            f"{cur.fetchone()[0]:,}"
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print()
    print("=" * 80)
    print("🚀 ETL — PARQUET → POSTGRESQL")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. Carregar Parquet
    # -------------------------------------------------------------------------

    df = carregar_parquet()

    # -------------------------------------------------------------------------
    # 2. Normalizar
    # -------------------------------------------------------------------------

    df = normalizar_dataframe(df)

    # -------------------------------------------------------------------------
    # 3. Conectar ao PostgreSQL
    # -------------------------------------------------------------------------

    with get_connection() as conn:

        try:

            # -----------------------------------------------------------------
            # 4. Buscar fonte
            # -----------------------------------------------------------------

            fonte_id = buscar_fonte(conn)

            print()
            print(
                f"Fonte ID: {fonte_id}"
            )

            # -----------------------------------------------------------------
            # 5. Dimensões
            # -----------------------------------------------------------------

            inserir_dimensoes(
                conn,
                df,
                fonte_id,
            )

            # -----------------------------------------------------------------
            # 6. Fatos
            # -----------------------------------------------------------------

            inserir_fatos(
                conn,
                df,
                fonte_id,
            )

            # -----------------------------------------------------------------
            # 7. Validação
            # -----------------------------------------------------------------

            validar_banco(conn)

            # -----------------------------------------------------------------
            # 8. Commit
            # -----------------------------------------------------------------

            conn.commit()

        except Exception:

            conn.rollback()

            print()
            print("=" * 80)
            print("❌ TRANSAÇÃO CANCELADA")
            print("=" * 80)
            print(
                "Nenhuma alteração desta execução "
                "foi confirmada no PostgreSQL."
            )

            raise

    print()
    print("=" * 80)
    print("✅ ETL FINALIZADO")
    print("=" * 80)


# =============================================================================
# EXECUÇÃO
# =============================================================================

if __name__ == "__main__":
    main()