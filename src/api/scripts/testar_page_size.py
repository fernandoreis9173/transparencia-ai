from src.api.scripts.despesas_extractor import DespesasExtractor

extractor = DespesasExtractor()

tamanhos = [50, 100, 200, 500]

for tamanho in tamanhos:
    print(f"\n{'=' * 50}")
    print(f"Testando page_size={tamanho}")

    try:
        resposta = extractor.consultar(
            ano=2025,
            tipo_retorno="favorecido",
            page=1,
            page_size=tamanho,
            cod_orgao=None,
            cod_funcao=None,
        )

        items = resposta.get("items", [])

        print(f"Registros recebidos: {len(items)}")
        print(f"Total informado: {resposta.get('totalItems')}")
        print(f"Total de páginas: {resposta.get('totalPages')}")
        print(f"Page size informado: {resposta.get('pageSize')}")

    except Exception as erro:
        print(f"Erro: {erro}")