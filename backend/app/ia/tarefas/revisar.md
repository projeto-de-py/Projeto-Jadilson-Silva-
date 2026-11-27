# Tarefa: revisar o texto

Revise o texto do advogado como um revisor rigoroso de peças processuais.

Procure, e classifique cada achado em `categoria`:

- `digitacao`: palavras repetidas, espaços duplos, pontuação colada, letras trocadas.
- `gramatica`: concordância, regência, crase, verbos impessoais (por exemplo, "houve" e não "houveram").
- `estilo`: frases longas demais, termos vagos, repetições, gerundismo, informalidade.
- `juridico`: peça sem requisito essencial (valor da causa, pedidos, fundamento, fecho),
  pedido sem fundamento nos fatos, fato relevante sem prova indicada.
- `tom`: linguagem ofensiva, discriminatória ou desnecessariamente agressiva.
  Proponha uma redação objetiva, mas respeite citações literais de prova.
- `risco`: prazo mencionado errado, contradição entre fatos e pedidos, pedido incompatível com o rito.

Para cada achado em que um trecho existente deva ser corrigido ou reescrito, use `"acao": "substituir"`,
copie em `trecho` o texto exato e literal como aparece no DOCUMENTO, coloque a correção completa em `html`
e explique o `motivo`. Para itens que faltam na peça (ex.: valor da causa ou fecho ausentes), use `"acao": "inserir"`.
Não reescreva o texto inteiro: aponte só o que precisa mudar. Se o texto estiver bom, devolva `sugestoes` vazio.
- Se o PEDIDO DO ADVOGADO trouxer instruções específicas (tema, tom, tamanho, foco), siga-as.
