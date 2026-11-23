# ai-model: reconhecedor de entidades jurídicas (NER)

Componente de IA **treinado pela equipe** do sistema Jadilson Silva Adv. Não usa API externa de IA.

## O que ele faz

Dado um texto jurídico (relato do cliente, peça), devolve os trechos que são **PESSOA, ORGANIZACAO, LEGISLACAO, JURISPRUDENCIA, TEMPO ou LOCAL**, cada um com a posição no texto e uma **confiança** de 0 a 1, mostrada em três faixas:

| Faixa | Confiança | O que o app faz |
|---|---|---|
| alta (centro do alvo) | ≥ 90% | marca como identificado |
| média | 60% a 90% | marca como "conferir" |
| baixa | < 60% | marca como "incerto" |

Usos no app:
1. **Proteger dados:** trocar nomes de pessoas por `[NOME]` antes de o texto ir para o LLM externo (opcional, `IA_MASCARAR_NOMES=true`).
2. **Conferir citações:** destacar as leis e decisões citadas numa peça para o advogado conferir (`POST /api/ia/entidades`).

Ele **não** substitui o advogado nem confirma que uma lei ou decisão existe: só localiza o que parece citação.

## Problema, dados e técnica

- **Problema:** o LLM do app pode inventar citações e o texto do cliente sai do servidor com nomes. A regra atual só mascarava CPF, CNPJ, e-mail e telefone.
- **Dados:** [LeNER-Br](https://cic.unb.br/~teodecampos/LeNER-Br/), anotado à mão: 66 decisões de tribunais (STF, STJ, TJMG, TCU...) e 4 leis. Licença MIT ([repositório](https://github.com/peluz/lener-br)). 7.827 frases de treino, 1.176 de validação, 1.389 de teste. Não há dados de clientes do escritório.
- **Referência:** LUZ DE ARAUJO, P. H. et al. *LeNER-Br: a Dataset for Named Entity Recognition in Brazilian Legal Text.* PROPOR 2018.
- **Técnica:** classificação de cada palavra com etiquetas BIO (regressão logística treinada por gradiente, `scikit-learn`), usando atributos da palavra e das vizinhas (código em `backend/app/ia/ner/`). Escolhida por ser explicável, treinar em minutos em CPU comum e dar probabilidade por palavra.

## Resultados (conjunto de teste, uma única medição)

Métrica por entidade completa (`seqeval`): uma entidade só conta como certa se o trecho e o tipo coincidirem.

| Modelo | Precisão | Revocação | F1 |
|---|---|---|---|
| Baseline: dicionário (decora as entidades do treino) | 0,605 | 0,401 | 0,482 |
| **Modelo escolhido (atributos "completo", alpha 1e-6)** | 0,550 | 0,669 | **0,603** |

Por tipo de entidade:

| Tipo | Precisão | Revocação | F1 | Exemplos no teste |
|---|---|---|---|---|
| TEMPO | 0,915 | 0,844 | 0,878 | 192 |
| PESSOA | 0,742 | 0,777 | 0,759 | 233 |
| ORGANIZACAO | 0,604 | 0,683 | 0,641 | 501 |
| LEGISLACAO | 0,426 | 0,569 | 0,487 | 378 |
| JURISPRUDENCIA | 0,357 | 0,578 | 0,441 | 185 |
| LOCAL | 0,260 | 0,426 | 0,323 | 47 |

### Interpretação

- O modelo **supera o baseline em F1** (0,60 contra 0,48) porque generaliza para nomes e citações que nunca viu; o dicionário erra pouco, mas esquece muito (revocação 0,40).
- **Datas (TEMPO) e pessoas** funcionam bem. **Leis e decisões** são o ponto fraco: a precisão é baixa (0,43 e 0,36), ou seja, o modelo marca trechos a mais. Por isso o app trata essas marcações como **"conferir"**, nunca como confirmação.
- **LOCAL** tem poucos exemplos (47) e o resultado é instável.
- Para o uso proposto (**apoiar** a revisão do advogado, não decidir), a revocação de 0,68 a 0,84 em pessoas, órgãos e datas é útil; para mascarar dados pessoais **sozinho** ela **não** é suficiente (falha em cerca de 1 de cada 4 nomes). Por isso a máscara de nomes é opcional e complementa as regras de CPF/CNPJ/e-mail/telefone.

### Experimentos (F1 na validação)

Três conjuntos de atributos, comparados no conjunto de validação (o de teste só é usado no fim):

| Atributos | alpha 1e-7 | alpha 1e-6 |
|---|---|---|
| `palavra` (só a palavra) | 0,160 | 0,146 |
| `contexto` (+ 2 vizinhas de cada lado) | 0,453 | 0,466 |
| `completo` (+ prefixo, sufixo, formato, pares) | 0,512 | **0,535** |

- **Contexto é o que mais pesa:** sem as vizinhas, o modelo mal reconhece entidades (0,15); com elas, sobe para 0,47.
- Uma primeira rodada (alpha 1e-6 e 1e-5, 30 iterações) deu F1 de teste 0,602, praticamente igual: o modelo chegou a um **platô** com esse tipo de atributo.
- **O que não funcionou:** tentamos CRF (`sklearn-crfsuite`), o modelo de sequência padrão para NER, mas a biblioteca `python-crfsuite` não compila no Python 3.15 do Windows usado. Ficou como melhoria futura.

### Análise de erros (teste)

509 entidades perdidas (falsos negativos) e 842 marcações a mais (falsos positivos). Exemplos em `models/metricas_ner.json`. Padrões: nomes de órgãos longos (`Secretaria de Controle Externo da Defesa Nacional...`) são cortados no meio; nomes próprios separados em duas pessoas; e números soltos (`16/2016`) marcados como data. Em texto de petição (linguagem mais informal que a das decisões do treino) o desempenho tende a ser menor; **ainda não medimos isso**.

## Limitações

- Treinado em decisões de tribunais superiores e estaduais; petições e relatos de clientes têm outro estilo.
- Cada palavra é classificada **separadamente** (não é um modelo de sequência): entidades longas quebram. Próximo passo: CRF em outro ambiente ou BERTimbau no Colab.
- Não verifica se a lei existe, se está vigente ou se a decisão é real.
- Pode errar nomes próprios em qualquer direção; não deve ser a única proteção de dados pessoais.

## Como reproduzir

```
pip install -r ai-model/requirements.txt
python ai-model/scripts/baixar_lener.py     # baixa o LeNER-Br para datasets/lener_br/
python ai-model/scripts/treinar_ner.py      # baseline, experimentos, teste, modelo e métricas
```

Gera `ai-model/models/ner_juridico.joblib` (7 MB) e `ai-model/models/metricas_ner.json`. A semente é fixa (42): a mesma execução dá o mesmo resultado.

## Estrutura

```
ai-model/
  scripts/baixar_lener.py     baixa os dados
  scripts/treinar_ner.py      baseline, experimentos, avaliação e salvamento
  scripts/coletar_dados.py    protótipo anterior: ementas públicas anonimizadas (classificador de área, descartado)
  scripts/anonimizar.py       anonimização por regras usada na coleta
  models/                     modelo treinado e métricas
backend/app/ia/ner/           código usado no treino E no app (tokenização, atributos, modelo, serviço)
```

## Privacidade (LGPD)

O texto enviado a `POST /api/ia/entidades` é processado **em memória** e não é gravado nem registrado em log. O modelo foi treinado só com documentos públicos.
