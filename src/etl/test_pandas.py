import pandas as pd

print("Pandas funcionando!")

dados = {
    "cidade": [
        "São Paulo",
        "Campinas",
        "Santos"
    ],
    "gasto": [
        1000000,
        500000,
        300000
    ]
}

df = pd.DataFrame(dados)

print(df)