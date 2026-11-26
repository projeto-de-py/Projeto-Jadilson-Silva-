# Arquitetura: módulo de IA (NER jurídico)

> Documento de arquitetura/estudo. IA real, NER e MinutaIA **não** participam do
> fluxo entregue; estado final em [RELATORIO_ENTREGA.md](RELATORIO_ENTREGA.md).

Projeto Integrador de IA. Como o app era, como o módulo novo entra e por quê.

> Histórico: a primeira ideia foi um classificador de área (Trabalhista, Bancário, Previdenciário). Foi **descartada**: o advogado já escolhe a área ao criar o documento e o LLM se adapta a ela, então não resolvia problema real. O protótipo de coleta (`ai-model/scripts/coletar_dados.py`) mostrou dados viáveis, mas ficou como experimento. Ver `ai-model/README.md`.

## 1. Problema

O LLM do app (Gemma via OpenRouter) escreve bem, mas:
1. pode **citar leis e decisões que não existem**; hoje só há o aviso `[CONFIRA A FONTE]`;
2. recebe o texto do cliente **com nomes**: a regra atual mascarava só CPF, CNPJ, e-mail e telefone.

## 2. O que a IA da equipe faz

Um reconhecedor de entidades (NER) treinado com o LeNER-Br acha, no texto, **pessoas, organizações, leis, decisões, datas e locais**, com posição e confiança. Usos:

- **Proteger:** trocar PESSOA por `[NOME]` antes de enviar ao LLM (`IA_MASCARAR_NOMES=true`, opcional).
- **Conferir:** destacar as leis e decisões citadas, com faixa de confiança, para o advogado conferir.

O LLM **escreve**; a IA da equipe **localiza e protege**. Uma não substitui a outra.

## 3. Arquitetura

```
 OFFLINE (ai-model/, reproduzível)                    ONLINE (dentro do app)
 ┌──────────────────────────────────┐
 │ baixar_lener.py → datasets/      │       React (Editor de documentos)
 │ treinar_ner.py                   │         └─ "Conferir citações" ── POST ──┐
 │   baseline (dicionário)          │                                           ▼
 │   experimentos (atributos×alpha) │       routes/ia.py  POST /api/ia/entidades
 │   teste, análise de erros        │          sessão + CSRF + limite 30/min + validação
 │            ▼                     │                          ▼
 │ models/ner_juridico.joblib       │       app/ia/ner/servico.py  (carrega 1x, sob demanda)
 │ models/metricas_ner.json  ───────────────▶   tokenizador → atributos → modelo (probabilidade
 └──────────────────────────────────┘          por palavra) → agrupa BIO → entidades + confiança
                                                          ▼
                              { entidades[], contagem, versao_modelo, aviso }   (nada é gravado)

 Proteção no fluxo do LLM (opcional):
   texto → regras (CPF/CNPJ/e-mail/telefone) → [modelo NER: PESSOA → [NOME]] → provedor externo
```

O código de tokenização e atributos é **o mesmo** no treino e no app (`backend/app/ia/ner/`): isso evita o erro clássico de o modelo treinar de um jeito e ser usado de outro.

### Contrato da API

| Método | Rota | Corpo | Resposta | Erros |
|---|---|---|---|---|
| POST | `/api/ia/entidades` | `{texto: str (1 a 20.000)}` | `{entidades[{tipo, texto, inicio, fim, confianca, faixa}], contagem, versao_modelo, aviso}` | 401 sem sessão, 403 CSRF, 422 texto inválido, 429 limite, 503 modelo ausente (com a instrução de como gerá-lo) |

### Decisões e trade-offs

| Decisão | Escolhido | Alternativa | Por quê / custo |
|---|---|---|---|
| Onde roda | No backend, arquivo `.joblib` | Serviço separado | O backend já é Python; sem deploy extra. Custo: depende de scikit-learn no servidor |
| Algoritmo | Regressão logística por palavra, com atributos de contexto | CRF; BERTimbau | Treina em minutos, dá probabilidade por palavra. O CRF não compilou no Python 3.15 do Windows; BERTimbau exige GPU (Colab). Custo: ignora a ordem das etiquetas, então entidades longas quebram |
| Dados | LeNER-Br (público, anotado à mão, MIT) | Dados de clientes | LGPD: nenhum dado de cliente. Custo: estilo diferente de petição |
| Confiança | Faixas alta / média / baixa | Sempre afirmar | A IA apoia o advogado; item incerto vira "conferir" |
| Máscara de nomes | Opcional, desligada por padrão | Sempre ligada | Ligada, a peça volta com `[NOME]` no lugar do cliente. A revocação de 78% não basta como única proteção |
| Modelo ausente | App segue funcionando; entidades respondem 503 | Falhar no startup | O módulo é um recurso, não o núcleo do app |

## 4. Resultados

Teste do LeNER-Br: F1 **0,603** (baseline dicionário: 0,482). Melhores tipos: TEMPO 0,88 e PESSOA 0,76; pior: LOCAL 0,32. Tabelas, experimentos, análise de erros e limitações em `ai-model/README.md`.

## 5. Riscos

1. **Precisão baixa em leis (0,43) e decisões (0,36):** marca trechos a mais. Tratado como "conferir".
2. **Diferença de domínio:** treinado em decisões; petições e relatos são mais informais. **Ainda não medido** com texto próprio.
3. **Nomes não pegos:** 22% das pessoas passam; a máscara não é proteção única.
4. **"Não encontrada" não é "falsa":** o módulo não verifica existência nem vigência de lei ou decisão.

## 6. Próximos passos

- Medir o modelo com um conjunto de textos escritos pela equipe (declarados como tais).
- Experimento de melhoria: modelo de sequência (CRF em outro ambiente) ou BERTimbau no Colab.
- Conferência de existência: lista curta de leis-chave (CLT, CDC, Lei 8.213/91, Constituição); o repositório `ctresb/leis` fica como trabalho futuro.
- Extrair datas do relato para sugerir uma cronologia do caso.
- Roadmap do briefing de produto (fora do escopo desta entrega): upload de documentos, contexto persistente do caso, painel de inconsistências, OCR.
