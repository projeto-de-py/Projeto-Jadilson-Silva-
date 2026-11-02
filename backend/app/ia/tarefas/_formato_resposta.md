# Formato da resposta (vale para todas as tarefas)

Responda SOMENTE com um objeto JSON válido, sem texto antes ou depois, neste formato:

```json
{
  "perguntas": ["pergunta objetiva, se faltar contexto essencial"],
  "sugestoes": [
    {
      "titulo": "até 80 caracteres",
      "previa": "uma ou duas frases resumindo a sugestão",
      "html": "<p>texto a acrescentar</p>",
      "tipo": "Trecho | Resumo | Revisão | Aviso",
      "categoria": "digitacao | gramatica | estilo | juridico | tom | risco | conteudo",
      "severidade": "info | atencao | critica",
      "trecho": "trecho original a que a sugestão se refere, se houver",
      "motivo": "por que a mudança é recomendada"
    }
  ]
}
```

Regras do campo `html`: use apenas `<p>`, `<h2>`, `<h3>`, `<ol>`, `<ul>`, `<li>`, `<strong>`, `<em>`,
`<br>` e `<blockquote>`. Nenhum atributo, nenhum script, nenhum link.

Se houver `perguntas`, devolva `sugestoes` vazio: pergunte antes de redigir.
