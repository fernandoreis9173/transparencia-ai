import requests
import json


URL = "https://www.transparencia.sp.gov.br/Despesas/Buscar"


def consultar(cpf_cnpj, ano=2025):
    payload = {
        "tipoRetorno": "favorecido",
        "anoExercicio": ano,
        "dataInicio": None,
        "dataTermino": None,
        "codigoFiltro": None,
        "nomeFavorecido": None,
        "cpfCnpjFavorecido": cpf_cnpj,
        "codOrgao": 48000,
        "codFuncao": 12,
        "codSubfuncao": None,
        "codPrograma": None,
        "codAcao": None,
        "codElemento": None,
        "page": 1,
        "pageSize": 50,
        "totalItens": 0,
    }

    response = requests.post(
        URL,
        json=payload,
        timeout=60,
    )

    print("Status:", response.status_code)

    response.raise_for_status()

    return response.json()


def main():

    favorecidos = {
        "2P2L ENGENHARIA LTDA": "26875439000151",
        "18 GIGAS COMERCIO DE EQUIPAMENTOS LTDA": "20174368000183",
    }

    for nome, cpf_cnpj in favorecidos.items():

        print()
        print("=" * 70)
        print(nome)
        print("=" * 70)

        dados = consultar(cpf_cnpj)

        print()
        print("TIPO DA RESPOSTA:")
        print(type(dados))

        print()
        print("CHAVES DA RESPOSTA:")

        if isinstance(dados, dict):
            for chave in dados.keys():
                print(f" - {chave}")

        print()
        print("RESPOSTA COMPLETA:")

        print(
            json.dumps(
                dados,
                ensure_ascii=False,
                indent=2,
            )[:15000]
        )


if __name__ == "__main__":
    main()