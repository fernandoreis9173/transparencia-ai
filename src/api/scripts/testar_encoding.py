from api.scripts.despesas_extractor import DespesasExtractor


def main():

    extractor = DespesasExtractor()

    resultado = extractor.consultar(
        ano=2025,
        tipo_retorno="favorecido",
        page=1,
        page_size=50,
        cod_orgao=48000,
        cod_funcao=12,
    )

    registros = extractor._extrair_registros(resultado)

    for registro in registros[:20]:

        nome = registro.get(
            "nome_favorecido"
        )

        cpf_cnpj = registro.get(
            "cnpj_cpf_favorecido"
        )

        print(
            repr(nome),
            "|",
            cpf_cnpj,
        )


if __name__ == "__main__":
    main()