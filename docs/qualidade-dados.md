# Qualidade dos Dados

## QD001 — Duplicidade de empenhos

Regra:

COUNT(DISTINCT num_empenho) = COUNT(*)

## QD002 — Empenho obrigatório

`num_empenho` não pode ser nulo.

## QD003 — Favorecido

`cnpj_cpf_favorecido` não pode ser nulo.

## QD004 — Valor empenhado

`vl_empenhado` não pode ser nulo.

## QD005 — Anomalia de liquidação

Identificar:

vl_liquidado > vl_empenhado

## QD006 — Anomalia de pagamento

Identificar:

vl_pago > vl_liquidado

## QD007 — Ano

`ano_exercicio` deve corresponder ao ano solicitado na extração.