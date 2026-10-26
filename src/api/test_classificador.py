
from src.api.services.gemini_service import classificar_pergunta


testes = {
    "Como está a situação dos pagamentos?": "situacao_pagamento",
    "Quais pagamentos estão pendentes?": "situacao_pagamento",
    "Quantos empenhos foram pagos?": "situacao_pagamento",
    "Quais são as anomalias?": "anomalias",
    "Mostre a evolução mensal das despesas": "evolucao_mensal",
    "Quais fornecedores receberam mais?": "top_favorecidos",
    "Quais são os maiores empenhos?": "maiores_empenhos",
    "Quais unidades orçamentárias gastaram mais?": "unidades",
    "Qual é o resumo geral das despesas?": "resumo",
}

for pergunta, esperado in testes.items():
    resultado = classificar_pergunta(pergunta)
    status = "OK" if resultado == esperado else "FALHOU"

    print(
        f"[{status}] {pergunta} "
        f"| esperado={esperado} "
        f"| recebido={resultado}"
    )
