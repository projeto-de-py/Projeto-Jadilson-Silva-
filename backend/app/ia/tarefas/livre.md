# Tarefa: atender o pedido do advogado

O advogado escreveu um pedido livre. **Faça exatamente o que ele pediu**, no assunto, no tom e na extensão pedidos.

- Leia o PEDIDO DO ADVOGADO com atenção e responda a ele, e não a outra coisa. Não troque o pedido por "continuar a peça"
  nem por um resumo genérico.
- Use o DOCUMENTO aberto e os dados do caso como contexto (nomes, valores, datas, fase). Não invente o que não estiver lá;
  use `[COLCHETES]` para lacunas.
- Se o pedido for um texto a inserir (um parágrafo, uma seção, uma cláusula, uma petição), entregue o texto pronto em `html`.
- Se o pedido for uma pergunta ou pedir uma análise, entregue a resposta objetiva em `html` (tipo "Trecho" ou "Resumo")
  e aponte o que o advogado deve conferir.
- Se o pedido for ambíguo ou faltar dado essencial, faça UMA pergunta objetiva em `perguntas` e devolva `sugestoes` vazio.
- Se o pedido for impossível ou fora do escopo jurídico, diga isso em uma sugestão do tipo "Aviso", sem inventar.
