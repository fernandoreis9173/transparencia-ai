from src.api.scripts.despesas_extractor import DespesasExtractor


def main():
    extractor = DespesasExtractor(
        timeout=60,
        max_retries=3,
        delay=0.2,
    )

    resultado = extractor.consultar(
        ano=2025,
        tipo_retorno="favorecido",
        page=1,
        page_size=50,
        cod_orgao=None,
        cod_funcao=None,
    )

    print("Total de registros:", resultado["totalItems"])
    print("Total de páginas:", resultado.get("totalPages"))
    print("Quantidade retornada:", len(resultado["items"]))

    print("\nPrimeiros registros:")

    for item in resultado["items"][:5]:
        print(item)


if __name__ == "__main__":
    main()