import requests
import pandas as pd
import time

URL = "https://www.transparencia.sp.gov.br/Despesas/Buscar"

favorecidos = [
    "23332812866",
    "50547018851",
    "60629992000142",
    "67431718000103",
    "02456361000172",
    "22770554000100",
    "23622391000181",
    "11078095000182",
]

for cpf_cnpj in favorecidos:

    print("\n" + "=" * 70)
    print(f"Consultando favorecido: {cpf_cnpj}")

    payload = {
        "tipoRetorno": "favorecido",
        "anoExercicio": 2025,
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
        "totalItens": 0
    }

    try:
        response = requests.post(
            URL,
            json=payload,
            timeout=60
        )

        data = response.json()

        print("Status:", response.status_code)
        print("Etapa:", data.get("etapaAtual"))
        print("Total de empenhos:", data.get("totalItems"))
        print("Total de páginas:", data.get("totalPages"))

        items = data.get("items", [])

        if items:

            df = pd.DataFrame(items)

            print("\nEmpenhos encontrados:")

            colunas = [
                "num_empenho",
                "data_registro_empenho",
                "vl_empenhado",
                "vl_liquidado",
                "vl_pago",
                "cod_funcao",
                "cod_subfuncao",
                "cod_programa",
                "cod_acao",
            ]

            colunas_existentes = [
                c for c in colunas
                if c in df.columns
            ]

            print(
                df[colunas_existentes]
                .to_string(index=False)
            )

        time.sleep(0.5)

    except Exception as e:
        print("Erro:", e)