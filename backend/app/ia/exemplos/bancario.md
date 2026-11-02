# Exemplos (few-shot): bancário e consumidor

Os exemplos abaixo mostram o NÍVEL e o FORMATO esperados. Não copie o conteúdo: use o contexto do pedido atual.

## Exemplo 1: revisar

DOCUMENTO: "O banco cobrou juros abusivos de 5,2% ao mês no contrato de [DATA], por isso requer a revisão."

RESPOSTA:
```json
{
  "perguntas": [],
  "sugestoes": [
    {
      "titulo": "Falta comparar com a taxa média de mercado",
      "previa": "A abusividade se demonstra pela diferença para a taxa média do Banco Central na época.",
      "html": "<p>A taxa contratada, de 5,2% ao mês, supera a taxa média de mercado divulgada pelo Banco Central do Brasil para a modalidade na data da contratação, de [TAXA MÉDIA]% ao mês.</p>",
      "tipo": "Trecho",
      "categoria": "juridico",
      "severidade": "atencao",
      "trecho": "juros abusivos de 5,2% ao mês",
      "motivo": "Chamar a taxa de abusiva sem o parâmetro de mercado enfraquece o pedido."
    }
  ]
}
```

## Exemplo 2: citação de jurisprudência

Quando a sugestão mencionar súmula, tema ou julgado, inclua `[CONFIRA A FONTE]` ao lado da referência e não invente número:

```json
{
  "perguntas": [],
  "sugestoes": [
    {
      "titulo": "Aplicação do CDC aos bancos",
      "previa": "Fundamentar a aplicação do CDC às instituições financeiras.",
      "html": "<p>O Código de Defesa do Consumidor se aplica às instituições financeiras [CONFIRA A FONTE: súmula do STJ sobre o tema].</p>",
      "tipo": "Trecho",
      "categoria": "juridico",
      "severidade": "info",
      "motivo": "A relação entre banco e cliente é de consumo; a referência exata deve ser conferida antes de citar."
    }
  ]
}
```
