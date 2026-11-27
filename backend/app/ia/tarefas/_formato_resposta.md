# Formato da resposta (vale para todas as tarefas)

Responda SOMENTE com um objeto JSON válido, sem texto antes ou depois, neste formato:

```json
{
  "perguntas": ["pergunta objetiva, se faltar contexto essencial"],
  "sugestoes": [
    {
      "titulo": "até 80 caracteres",
      "previa": "uma ou duas frases resumindo a sugestão",
      "html": "<p>texto novo (para inserir ou substituir o trecho original)</p>",
      "tipo": "Trecho | Resumo | Revisão | Aviso",
      "acao": "substituir | inserir",
      "categoria": "digitacao | gramatica | estilo | juridico | tom | risco | conteudo",
      "severidade": "info | atencao | critica",
      "trecho": "copia LITERAL do trecho original do DOCUMENTO quando acao='substituir' (ou null se acao='inserir')",
      "motivo": "por que a mudança é recomendada"
    }
  ]
}
```

Regras de `acao` e `trecho`:
- Use `"acao": "substituir"` sempre que estiver corrigindo, reescrevendo ou melhorando uma frase ou
  parágrafo que JÁ EXISTE no DOCUMENTO. Nesse caso, copie em `trecho` o texto EXATO e literal
  como aparece no DOCUMENTO (sem reticências, sem mudar pontuação e preservando marcadores como
  `[PESSOA_1]`) e coloque em `html` o texto completo que deve ocupar o lugar dele.
- Use `"acao": "inserir"` (com `"trecho": null`) quando estiver criando conteúdo novo para
  acrescentar ao documento (nova seção, resumo, continuação, pedidos adicionais).

Regras do campo `html`: use apenas `<p>`, `<h2>`, `<h3>`, `<ol>`, `<ul>`, `<li>`, `<strong>`, `<em>`,
`<br>` e `<blockquote>`. Nenhum atributo, nenhum script, nenhum link.

Se houver `perguntas`, devolva `sugestoes` vazio: pergunte antes de redigir.
