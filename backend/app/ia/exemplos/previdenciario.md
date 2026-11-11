# Exemplos (few-shot): previdenciário

Os exemplos abaixo mostram o NÍVEL e o FORMATO esperados. Não copie o conteúdo: use o contexto do pedido atual.

## Exemplo 1: continuar a peça

DOCUMENTO: "I – DOS FATOS. O autor requereu o auxílio por incapacidade temporária em [DER] (NB [NÚMERO]) e o INSS indeferiu por falta de incapacidade, embora os laudos anexos indiquem o contrário."

RESPOSTA:
```json
{
  "perguntas": [],
  "sugestoes": [
    {
      "titulo": "Seção do direito e requisitos legais",
      "previa": "Falta demonstrar qualidade de segurado, carência e incapacidade.",
      "html": "<h2>II – DO DIREITO</h2><p>Estão presentes os requisitos dos arts. 59 e seguintes da Lei nº 8.213/91: qualidade de segurado, carência e incapacidade para o trabalho, esta comprovada pelos laudos e atestados anexos.</p>",
      "tipo": "Trecho",
      "categoria": "juridico",
      "severidade": "info",
      "motivo": "Os fatos já foram narrados; o próximo passo é ligá-los aos requisitos legais."
    }
  ]
}
```

## Exemplo 2: dado essencial ausente

PEDIDO: "resuma o processo"  ·  sem caso vinculado

RESPOSTA:
```json
{ "perguntas": ["Qual processo devo resumir? Vincule um caso ou envie o número do benefício (NB) e a DER."], "sugestoes": [] }
```
