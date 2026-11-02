# Exemplos (few-shot): trabalhista

Os exemplos abaixo mostram o NÍVEL e o FORMATO esperados. Não copie o conteúdo: use o contexto do pedido atual.

## Exemplo 1: revisar

DOCUMENTO: "A reclamante foi admitida em [DATA] e trabalhava de segunda a sabado das 8h as 20h, sem intervalo , o que gerou horas extras."

RESPOSTA:
```json
{
  "perguntas": [],
  "sugestoes": [
    {
      "titulo": "Intervalo e horas extras sem base nos fatos",
      "previa": "A jornada alegada gera horas extras, mas faltam datas, função e o valor do salário.",
      "html": "<p>Detalhar a jornada: horário de entrada e saída, intervalo efetivamente gozado e a média semanal de horas extras, para sustentar o pedido certo e determinado (art. 840, §1º, da CLT).</p>",
      "tipo": "Revisão",
      "categoria": "juridico",
      "severidade": "atencao",
      "trecho": "trabalhava de segunda a sabado das 8h as 20h, sem intervalo",
      "motivo": "O pedido de horas extras precisa de jornada, período e valor indicados."
    },
    {
      "titulo": "Espaço antes da vírgula",
      "previa": "Há um espaço antes de vírgula.",
      "html": "<p>sem intervalo, o que gerou horas extras.</p>",
      "tipo": "Revisão",
      "categoria": "digitacao",
      "severidade": "info",
      "trecho": "sem intervalo , o que",
      "motivo": "Em português não se deixa espaço antes da vírgula."
    }
  ]
}
```

## Exemplo 2: contexto insuficiente (pergunta em vez de inventar)

PEDIDO: "redija a contestação"  ·  DOCUMENTO: vazio  ·  sem caso vinculado

RESPOSTA:
```json
{ "perguntas": ["O que o reclamante alegou na inicial? Vincule o caso ou cole o resumo dos pedidos."], "sugestoes": [] }
```
