from pathlib import Path
import json
import time

import pandas as pd

from api.scripts.despesas_extractor import DespesasExtractor
from datetime import datetime


ANO = 2025
COD_ORGAO = 48000
COD_FUNCAO = 12

PAGE_SIZE = 50

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"

FAVORECIDOS_FILE = (
    RAW_DIR
    / "favorecidos_2025_orgao_48000_funcao_12.csv"
)

EMPENHOS_DIR = RAW_DIR / "empenhos"

CHECKPOINT_DIR = (
    BASE_DIR / "data" / "output" / "checkpoints"
)

CHECKPOINT_FILE = (
    CHECKPOINT_DIR
    / "empenhos_2025_orgao_48000_funcao_12.json"
)

def agora():

    return datetime.now().isoformat(
        timespec="seconds"
    )
    
def criar_checkpoint():

    return {
        "indice": 0,
        "processados": 0,
        "erros": 0,
        "inicio": agora(),
        "ultima_atualizacao": agora(),
        "falhas": [],
    }


def carregar_checkpoint():

    if not CHECKPOINT_FILE.exists():

        return criar_checkpoint()

    with open(
        CHECKPOINT_FILE,
        "r",
        encoding="utf-8",
    ) as arquivo:

        checkpoint = json.load(arquivo)

    # Compatibilidade com checkpoint antigo
    checkpoint.setdefault(
        "indice",
        0,
    )

    checkpoint.setdefault(
        "processados",
        0,
    )

    checkpoint.setdefault(
        "erros",
        0,
    )

    checkpoint.setdefault(
        "inicio",
        agora(),
    )

    checkpoint.setdefault(
        "ultima_atualizacao",
        agora(),
    )

    checkpoint.setdefault(
        "falhas",
        [],
    )

    return checkpoint


def salvar_checkpoint(checkpoint):

    checkpoint["ultima_atualizacao"] = agora()

    CHECKPOINT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        CHECKPOINT_FILE,
        "w",
        encoding="utf-8",
    ) as arquivo:

        json.dump(
            checkpoint,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )


def main():

    print("=" * 70)
    print("EXTRAÇÃO DE EMPENHOS")
    print("=" * 70)

    if not FAVORECIDOS_FILE.exists():

        raise FileNotFoundError(
            "Arquivo de favorecidos não encontrado: "
            f"{FAVORECIDOS_FILE}"
        )

    df_favorecidos = pd.read_csv(
        FAVORECIDOS_FILE,
        dtype={
            "cnpj_cpf_favorecido": str
        },
    )

    print(
        f"Favorecidos: {len(df_favorecidos)}"
    )

    extractor = DespesasExtractor(
        timeout=60,
        max_retries=3,
        delay=0.2,
    )

    checkpoint = carregar_checkpoint()

    inicio = checkpoint["indice"]

    print(
        f"Iniciando no índice: {inicio}"
    )

    EMPENHOS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # for indice in range(
    #     inicio,
    #     len(df_favorecidos),
    # ):
    
    limite_teste = min(
    inicio + 100,
    len(df_favorecidos),
    )

    for indice in range(
        inicio,
        limite_teste,
    ):

        row = df_favorecidos.iloc[indice]

        cpf_cnpj = str(
            row["cnpj_cpf_favorecido"]
        ).strip()

        nome = str(
            row["nome_favorecido"]
        ).strip()

        print()
        print("-" * 70)

        print(
            f"[{indice + 1}/{len(df_favorecidos)}]"
        )

        print(
            f"Favorecido: {nome}"
        )

        print(
            f"CPF/CNPJ: {cpf_cnpj}"
        )

        try:

            df_empenhos = extractor.buscar_empenhos(
                ano=ANO,
                cpf_cnpj=cpf_cnpj,
                page_size=PAGE_SIZE,
                cod_orgao=COD_ORGAO,
                cod_funcao=COD_FUNCAO,
            )

            if not df_empenhos.empty:

                # Adiciona informações do favorecido
                if "cnpj_cpf_favorecido" not in df_empenhos:
                    df_empenhos[
                        "cnpj_cpf_favorecido"
                    ] = cpf_cnpj

                if "nome_favorecido" not in df_empenhos:
                    df_empenhos[
                        "nome_favorecido"
                    ] = nome

                arquivo = (
                    EMPENHOS_DIR
                    / f"{cpf_cnpj}.csv"
                )

                df_empenhos.to_csv(
                    arquivo,
                    index=False,
                    encoding="utf-8-sig",
                )

                print(
                    f"Empenhos encontrados: "
                    f"{len(df_empenhos)}"
                )

            else:

                print(
                    "Nenhum empenho encontrado."
                )

            checkpoint["indice"] = indice + 1

            checkpoint["processados"] += 1

            salvar_checkpoint(checkpoint)

        except Exception as erro:

            print(
                f"ERRO: {erro}"
            )

            checkpoint["erros"] += 1

            checkpoint["falhas"].append(
                {
                    "indice": indice,
                    "cpf_cnpj": cpf_cnpj,
                    "nome": nome,
                    "erro": str(erro),
                }
            )

            checkpoint["indice"] = indice + 1

            salvar_checkpoint(checkpoint)

            continue

    print()
    print("=" * 70)
    print("EXTRAÇÃO FINALIZADA")
    print("=" * 70)

    print(
        f"Processados: "
        f"{checkpoint['processados']}"
    )

    print(
        f"Erros: "
        f"{checkpoint['erros']}"
    )


if __name__ == "__main__":
    main()