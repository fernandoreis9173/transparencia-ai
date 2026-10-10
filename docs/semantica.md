# Semântica dos Dados

## Unidade de análise

A unidade de análise da tabela de fatos é o empenho individual.

Cada registro representa um empenho identificado por `num_empenho`.

## Valores financeiros

### vl_empenhado

Valor do empenho registrado para a despesa.

### vl_empenhado_inicial

Valor inicial registrado para o empenho antes de eventuais operações
de reforço ou anulação.

### vl_reforco

Valor acrescentado ao empenho por operação de reforço.

O SIAFEM possui operação específica de Reforço de Empenho.

### vl_anulacao

Valor correspondente à anulação do empenho.

O SIAFEM possui operação específica de Anulação de Empenho.

### vl_liquidado

Valor da despesa na fase de liquidação.

### vl_pago

Valor efetivamente pago referente ao empenho.

### vl_pago_rp

Valor pago relacionado a Restos a Pagar.

Este campo deve ser mantido separado de `vl_pago`.

## Item de despesa

### cod_item

Código do Item de Despesa integrante da classificação da despesa.

### nome_item

Descrição do Item de Despesa.

O Item de Despesa não deve ser interpretado automaticamente como
produto físico adquirido.

## Restos a Pagar

### indicador_restos

Indicador fornecido pela fonte relacionado à situação de Restos a Pagar.

Os valores devem ser preservados exatamente conforme retornados pela
fonte até que o domínio completo dos códigos seja confirmado.

## Valores de origem

Os valores financeiros devem ser preservados conforme disponibilizados
pela fonte oficial.

Não devem ser corrigidos, arredondados ou substituídos artificialmente.

## Anomalias

Registros em que `vl_liquidado > vl_empenhado` não devem ser
automaticamente corrigidos.

Devem ser preservados e classificados como ocorrência de qualidade
dos dados para investigação posterior.