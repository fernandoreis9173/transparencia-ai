from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Permite executar:
# python src/etl/validar_dataset_postgres.py
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

def normalizar_numero(valor):
    """
    Normaliza valores numéricos para comparação.
    """
    if pd.isna(valor):
        return None

    return round(float(valor), 2)


def normalizar_texto(valor):
    """
    Normaliza textos para comparação.
    """
    if pd.isna(valor):
        return None

    return str(valor).strip()


def comparar_valores(valor_parquet, valor_banco):
    """
    Compara dois valores considerando NULL/None.
    """

    parquet = normalizar_numero(valor_parquet)
    banco = normalizar_numero(valor_banco)

    return parquet == banco


# =============================================================================
# CARREGAR PARQUET
# =============================================================================

def carregar_parquet():
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
# CARREGAR POSTGRESQL
# =============================================================================

def carregar_postgres(conn, fonte_id):
    print()
    print("=" * 80)
    print("🐘 CARREGANDO POSTGRESQL")
    print("=" * 80)

    query = """
        SELECT
            fd.num_empenho,

            fd.ano_exercicio,

            o.codigo AS cod_orgao,

            uo.codigo AS cod_uo,

            f.documento AS cnpj_cpf_favorecido,

            fn.codigo AS cod_funcao,

            sf.codigo AS cod_subfuncao,

            p.codigo AS cod_programa,

            a.codigo AS cod_acao,

            tl.codigo AS cod_tipo_licitacao,

            fd.cod_elemento,
            fd.cod_categoria_despesa,
            fd.cod_grupo,
            fd.cod_modalidade_aplicacao,
            fd.cod_item,
            fd.cod_fonte,
            fd.cod_fonte_detalhada,

            fd.num_processo,
            fd.data_registro_empenho,
            fd.indicador_restos,

            fd.vl_empenhado_inicial,
            fd.vl_empenhado,
            fd.vl_reforco,
            fd.vl_anulacao,

            fd.vl_liquidado,
            fd.vl_pago,
            fd.vl_pago_rp,
            fd.vl_dotacao_atual

        FROM core.fato_despesa fd

        LEFT JOIN core.orgao o
            ON o.id = fd.orgao_id

        LEFT JOIN core.unidade_orcamentaria uo
            ON uo.id = fd.unidade_orcamentaria_id

        LEFT JOIN core.favorecido f
            ON f.id = fd.favorecido_id

        LEFT JOIN core.funcao fn
            ON fn.id = fd.funcao_id

        LEFT JOIN core.subfuncao sf
            ON sf.id = fd.subfuncao_id

        LEFT JOIN core.programa p
            ON p.id = fd.programa_id

        LEFT JOIN core.acao a
            ON a.id = fd.acao_id

        LEFT JOIN core.tipo_licitacao tl
            ON tl.id = fd.tipo_licitacao_id

        WHERE fd.fonte_id = %s

        ORDER BY fd.num_empenho
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(fonte_id,),
    )

    print(
        f"Registros encontrados: {len(df):,}"
    )

    print(
        f"Colunas retornadas: {len(df.columns)}"
    )

    return df


# =============================================================================
# VALIDAR QUANTIDADE
# =============================================================================

def validar_quantidade(df_parquet, df_banco):

    print()
    print("=" * 80)
    print("1️⃣ VALIDANDO QUANTIDADE")
    print("=" * 80)

    total_parquet = len(df_parquet)
    total_banco = len(df_banco)

    print(
        f"Parquet     : {total_parquet:,}"
    )

    print(
        f"PostgreSQL  : {total_banco:,}"
    )

    if total_parquet == total_banco:
        print("✅ Quantidade de registros confere.")
        return True

    print("❌ Quantidade de registros NÃO confere.")

    return False


# =============================================================================
# VALIDAR DUPLICIDADE
# =============================================================================

def validar_duplicidade(df_parquet, df_banco):

    print()
    print("=" * 80)
    print("2️⃣ VALIDANDO DUPLICIDADE")
    print("=" * 80)

    duplicados_parquet = (
        df_parquet["num_empenho"]
        .duplicated()
        .sum()
    )

    duplicados_banco = (
        df_banco["num_empenho"]
        .duplicated()
        .sum()
    )

    print(
        f"Duplicados no Parquet    : "
        f"{duplicados_parquet}"
    )

    print(
        f"Duplicados no PostgreSQL : "
        f"{duplicados_banco}"
    )

    sucesso = (
        duplicados_parquet == 0
        and duplicados_banco == 0
    )

    if sucesso:
        print(
            "✅ Nenhum empenho duplicado."
        )
    else:
        print(
            "❌ Foram encontrados empenhos duplicados."
        )

    return sucesso


# =============================================================================
# VALIDAR EMPENHOS AUSENTES
# =============================================================================

def validar_empenhos(df_parquet, df_banco):

    print()
    print("=" * 80)
    print("3️⃣ VALIDANDO EMPENHOS")
    print("=" * 80)

    empenhos_parquet = set(
        df_parquet["num_empenho"]
        .dropna()
        .astype(str)
    )

    empenhos_banco = set(
        df_banco["num_empenho"]
        .dropna()
        .astype(str)
    )

    ausentes_banco = (
        empenhos_parquet
        - empenhos_banco
    )

    extras_banco = (
        empenhos_banco
        - empenhos_parquet
    )

    print(
        f"Empenhos no Parquet     : "
        f"{len(empenhos_parquet):,}"
    )

    print(
        f"Empenhos no PostgreSQL  : "
        f"{len(empenhos_banco):,}"
    )

    print(
        f"Ausentes no PostgreSQL  : "
        f"{len(ausentes_banco):,}"
    )

    print(
        f"Extras no PostgreSQL    : "
        f"{len(extras_banco):,}"
    )

    if ausentes_banco:
        print()
        print("Empenhos ausentes:")
        for empenho in sorted(ausentes_banco):
            print(
                f"   - {empenho}"
            )

    if extras_banco:
        print()
        print("Empenhos extras:")
        for empenho in sorted(extras_banco):
            print(
                f"   - {empenho}"
            )

    sucesso = (
        len(ausentes_banco) == 0
        and len(extras_banco) == 0
    )

    if sucesso:
        print(
            "✅ Todos os empenhos conferem."
        )
    else:
        print(
            "❌ Existem diferenças nos empenhos."
        )

    return sucesso


# =============================================================================
# VALIDAR COLUNAS
# =============================================================================

def validar_colunas(df_parquet, df_banco):

    print()
    print("=" * 80)
    print("4️⃣ VALIDANDO CAMPOS")
    print("=" * 80)

    campos = [
        "ano_exercicio",
        "cod_orgao",
        "cod_uo",
        "cnpj_cpf_favorecido",
        "cod_funcao",
        "cod_subfuncao",
        "cod_programa",
        "cod_acao",
        "cod_tipo_licitacao",
        "cod_elemento",
        "cod_categoria_despesa",
        "cod_grupo",
        "cod_modalidade_aplicacao",
        "cod_item",
        "cod_fonte",
        "cod_fonte_detalhada",
        "num_processo",
        "indicador_restos",
        "vl_empenhado_inicial",
        "vl_empenhado",
        "vl_reforco",
        "vl_anulacao",
        "vl_liquidado",
        "vl_pago",
        "vl_pago_rp",
        "vl_dotacao_atual",
    ]

    parquet_index = (
        df_parquet
        .copy()
        .assign(
            num_empenho=lambda x:
                x["num_empenho"].astype(str)
        )
        .set_index("num_empenho")
    )

    banco_index = (
        df_banco
        .copy()
        .assign(
            num_empenho=lambda x:
                x["num_empenho"].astype(str)
        )
        .set_index("num_empenho")
    )

    empenhos_comuns = sorted(
        set(parquet_index.index)
        & set(banco_index.index)
    )

    diferencas = []

    for empenho in empenhos_comuns:

        row_parquet = parquet_index.loc[
            empenho
        ]

        row_banco = banco_index.loc[
            empenho
        ]

        for campo in campos:

            valor_parquet = row_parquet[campo]
            valor_banco = row_banco[campo]

            # -------------------------------------------------------------
            # Campos numéricos
            # -------------------------------------------------------------

            campos_numericos = {
                "ano_exercicio",
                "cod_orgao",
                "cod_uo",
                "cod_funcao",
                "cod_subfuncao",
                "cod_programa",
                "cod_acao",
                "cod_tipo_licitacao",
                "cod_elemento",
                "cod_categoria_despesa",
                "cod_grupo",
                "cod_modalidade_aplicacao",
                "cod_item",
                "cod_fonte",
                "cod_fonte_detalhada",
                "vl_empenhado_inicial",
                "vl_empenhado",
                "vl_reforco",
                "vl_anulacao",
                "vl_liquidado",
                "vl_pago",
                "vl_pago_rp",
                "vl_dotacao_atual",
            }

            if campo in campos_numericos:

                if not comparar_valores(
                    valor_parquet,
                    valor_banco,
                ):
                    diferencas.append(
                        {
                            "num_empenho": empenho,
                            "campo": campo,
                            "parquet": valor_parquet,
                            "postgres": valor_banco,
                        }
                    )

            else:

                parquet_texto = (
                    normalizar_texto(
                        valor_parquet
                    )
                )

                banco_texto = (
                    normalizar_texto(
                        valor_banco
                    )
                )

                if parquet_texto != banco_texto:

                    diferencas.append(
                        {
                            "num_empenho": empenho,
                            "campo": campo,
                            "parquet": valor_parquet,
                            "postgres": valor_banco,
                        }
                    )

    print(
        f"Campos analisados: "
        f"{len(campos)}"
    )

    print(
        f"Empenhos comparados: "
        f"{len(empenhos_comuns):,}"
    )

    print(
        f"Diferenças encontradas: "
        f"{len(diferencas):,}"
    )

    if diferencas:

        print()
        print("❌ DIFERENÇAS ENCONTRADAS:")

        for diferenca in diferencas[:50]:

            print()
            print(
                f"Empenho: "
                f"{diferenca['num_empenho']}"
            )

            print(
                f"Campo: "
                f"{diferenca['campo']}"
            )

            print(
                f"Parquet: "
                f"{diferenca['parquet']}"
            )

            print(
                f"PostgreSQL: "
                f"{diferenca['postgres']}"
            )

        if len(diferencas) > 50:

            print()
            print(
                f"... e mais "
                f"{len(diferencas) - 50} diferenças."
            )

        return False

    print(
        "✅ Todos os campos conferem."
    )

    return True


# =============================================================================
# VALIDAR TOTAIS FINANCEIROS
# =============================================================================

def validar_totais(df_parquet, df_banco):

    print()
    print("=" * 80)
    print("5️⃣ VALIDANDO TOTAIS FINANCEIROS")
    print("=" * 80)

    campos = [
        "vl_empenhado",
        "vl_liquidado",
        "vl_pago",
        "vl_pago_rp",
    ]

    sucesso = True

    for campo in campos:

        total_parquet = (
            pd.to_numeric(
                df_parquet[campo],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

        total_banco = (
            pd.to_numeric(
                df_banco[campo],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

        diferenca = (
            float(total_parquet)
            - float(total_banco)
        )

        print()
        print(f"{campo}:")

        print(
            f"   Parquet     : "
            f"R$ {total_parquet:,.2f}"
        )

        print(
            f"   PostgreSQL  : "
            f"R$ {total_banco:,.2f}"
        )

        print(
            f"   Diferença   : "
            f"R$ {diferenca:,.2f}"
        )

        if abs(diferenca) > 0.01:

            sucesso = False

            print(
                "   ❌ Diferença encontrada."
            )

        else:

            print(
                "   ✅ Total confere."
            )

    return sucesso


# =============================================================================
# VALIDAR ANOMALIAS FINANCEIRAS
# =============================================================================

def validar_anomalias(df_parquet, df_banco):

    print()
    print("=" * 80)
    print("6️⃣ VALIDANDO ANOMALIAS FINANCEIRAS")
    print("=" * 80)

    parquet_anomalias = (
        (
            pd.to_numeric(
                df_parquet["vl_liquidado"],
                errors="coerce",
            )
            >
            pd.to_numeric(
                df_parquet["vl_empenhado"],
                errors="coerce",
            )
        )
        .fillna(False)
        .sum()
    )

    banco_anomalias = (
        (
            pd.to_numeric(
                df_banco["vl_liquidado"],
                errors="coerce",
            )
            >
            pd.to_numeric(
                df_banco["vl_empenhado"],
                errors="coerce",
            )
        )
        .fillna(False)
        .sum()
    )

    print(
        f"Parquet     : "
        f"{parquet_anomalias}"
    )

    print(
        f"PostgreSQL  : "
        f"{banco_anomalias}"
    )

    if parquet_anomalias == banco_anomalias:

        print(
            "✅ Quantidade de anomalias preservada."
        )

        return True

    print(
        "❌ Quantidade de anomalias diferente."
    )

    return False


# =============================================================================
# RELATÓRIO FINAL
# =============================================================================

def exibir_resultado(resultados):

    print()
    print("=" * 80)
    print("📋 RESULTADO FINAL DA VALIDAÇÃO")
    print("=" * 80)

    nomes = {
        "quantidade": "Quantidade de registros",
        "duplicidade": "Duplicidade",
        "empenhos": "Empenhos",
        "campos": "Campos",
        "totais": "Totais financeiros",
        "anomalias": "Anomalias financeiras",
    }

    for chave, resultado in resultados.items():

        status = "✅ APROVADO" if resultado else "❌ REPROVADO"

        print(
            f"{nomes[chave]:30} "
            f"{status}"
        )

    aprovado = all(
        resultados.values()
    )

    print()
    print("=" * 80)

    if aprovado:

        print(
            "🎉 DATASET VALIDADO COM SUCESSO"
        )

        print()
        print(
            "Parquet e PostgreSQL estão "
            "consistentes."
        )

    else:

        print(
            "⚠️ DATASET POSSUI DIVERGÊNCIAS"
        )

        print()
        print(
            "É necessário investigar "
            "as diferenças antes de "
            "prosseguir."
        )

    print("=" * 80)

    return aprovado


# =============================================================================
# MAIN
# =============================================================================

def main():

    print()
    print("=" * 80)
    print("🔎 VALIDAÇÃO — PARQUET × POSTGRESQL")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. Carregar Parquet
    # -------------------------------------------------------------------------

    df_parquet = carregar_parquet()

    # -------------------------------------------------------------------------
    # 2. Conectar ao PostgreSQL
    # -------------------------------------------------------------------------

    with get_connection() as conn:

        # ---------------------------------------------------------------------
        # 3. Buscar fonte
        # ---------------------------------------------------------------------

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT id
                FROM core.fonte
                WHERE codigo = %s
                """,
                (FONTE_CODIGO,),
            )

            resultado = cur.fetchone()

        if not resultado:

            raise RuntimeError(
                f"Fonte '{FONTE_CODIGO}' "
                "não encontrada."
            )

        fonte_id = resultado[0]

        print()
        print(
            f"Fonte ID: {fonte_id}"
        )

        # ---------------------------------------------------------------------
        # 4. Carregar PostgreSQL
        # ---------------------------------------------------------------------

        df_banco = carregar_postgres(
            conn,
            fonte_id,
        )

        # ---------------------------------------------------------------------
        # 5. Executar validações
        # ---------------------------------------------------------------------

        resultados = {}

        resultados["quantidade"] = (
            validar_quantidade(
                df_parquet,
                df_banco,
            )
        )

        resultados["duplicidade"] = (
            validar_duplicidade(
                df_parquet,
                df_banco,
            )
        )

        resultados["empenhos"] = (
            validar_empenhos(
                df_parquet,
                df_banco,
            )
        )

        resultados["campos"] = (
            validar_colunas(
                df_parquet,
                df_banco,
            )
        )

        resultados["totais"] = (
            validar_totais(
                df_parquet,
                df_banco,
            )
        )

        resultados["anomalias"] = (
            validar_anomalias(
                df_parquet,
                df_banco,
            )
        )

        # ---------------------------------------------------------------------
        # 6. Resultado
        # ---------------------------------------------------------------------

        aprovado = exibir_resultado(
            resultados
        )

    # -------------------------------------------------------------------------
    # Código de saída
    # -------------------------------------------------------------------------

    if not aprovado:
        sys.exit(1)


if __name__ == "__main__":
    main()