# Regras de Negócio

## RN01 — Unicidade do empenho

`num_empenho` deve identificar unicamente um empenho dentro da base
consolidada.

## RN02 — Granularidade

A tabela de fatos deve possuir um registro por empenho individual.

## RN03 — Valores financeiros

Os valores financeiros devem ser armazenados conforme fornecidos pela
fonte oficial.

Não aplicar correções manuais nos valores.

## RN04 — Reforço

`vl_reforco > 0` representa valor acrescentado ao empenho por operação
de reforço.

## RN05 — Anulação

`vl_anulacao > 0` representa valor correspondente à anulação do
empenho.

## RN06 — Relação entre valores

Deve ser monitorada a relação:

vl_empenhado =
vl_empenhado_inicial + vl_reforco - vl_anulacao

A relação deve ser tratada como regra de validação até que sua
aplicabilidade integral à base seja comprovada empiricamente.

## RN07 — Liquidação

`vl_liquidado` deve ser mantido exatamente como fornecido pela fonte.

Não aplicar limite artificial para impedir valores superiores a
`vl_empenhado`.

## RN08 — Pagamento

`vl_pago` representa o pagamento associado ao empenho.

`vl_pago_rp` deve ser tratado separadamente.

## RN09 — Restos a Pagar

Os valores de `indicador_restos` devem ser preservados conforme
retornados pela fonte.

Não atribuir significado aos códigos sem evidência documental.

## RN10 — Item de Despesa

`cod_item` e `nome_item` representam a classificação do Item de Despesa.

Não utilizar esses campos isoladamente para afirmar que determinado
produto físico foi adquirido.

## RN11 — Dados nulos

Valores nulos provenientes da fonte não devem ser automaticamente
convertidos para zero.

## RN12 — Qualidade

Devem ser gerados indicadores para situações potencialmente anômalas,
incluindo:

- `vl_liquidado > vl_empenhado`;
- divergência entre a fórmula de composição do empenho;
- classificação orçamentária incompleta;
- ausência de favorecido;
- ausência de processo;
- códigos de domínio não reconhecidos.