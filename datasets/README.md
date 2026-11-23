# Datasets

Só dados **públicos**. Não há dados de clientes do escritório.

## LeNER-Br (usado pelo modelo atual: NER jurídico)

| | |
|---|---|
| O que é | 66 decisões de tribunais (STF, STJ, TJMG, TCU...) e 4 leis, anotadas à mão com 6 tipos de entidade (formato BIO) |
| Tamanho | 7.827 frases de treino, 1.176 de validação, 1.389 de teste (cerca de 3 MB) |
| Licença | MIT (https://github.com/peluz/lener-br) |
| Referência | LUZ DE ARAUJO, P. H. et al. *LeNER-Br: a Dataset for Named Entity Recognition in Brazilian Legal Text.* PROPOR 2018. https://cic.unb.br/~teodecampos/LeNER-Br/ |
| Como obter | `python ai-model/scripts/baixar_lener.py` (grava em `datasets/lener_br/`, ignorado pelo git) |

## Ementas públicas (protótipo anterior, descartado)

Usadas só no protótipo do classificador de área, que foi descartado (ver `docs/ARQUITETURA_MODULO_IA.md`). Mantidas como experimento. Textos **reais e públicos** de decisões judiciais.

## Fontes

| Classe | Fonte | Licença / origem |
|---|---|---|
| Trabalhista | Ementas do TST, via `celsowm/jurisprudencias_tst` (Hugging Face) | Decisões públicas; **confirmar a licença na página do dataset e citar no relatório** |
| Previdenciário e Bancário | Ementas do TRF2, via `celsowm/jurisprudencias_trf2` (Hugging Face) | Idem |

Alternativa oficial testada: Portal de Dados Abertos do STJ (espelhos de acórdãos, CC-BY): `https://dadosabertos.web.stj.jus.br`.

Aviso: o dataset `celsowm/jurisprudencias_br` **não serve**: as ementas do TST estão como "removido no backend" e as do STJ/DJE estão vazias.

## Rótulos

Vêm dos **metadados** do tribunal (competência e assunto), nunca de palavras do texto. Detalhes em `ai-model/scripts/coletar_dados.py`.

## LGPD

- Finalidade: pesquisa acadêmica (Projeto Integrador).
- Minimização: só `texto` anonimizado e `rotulo` são gravados. Nome das partes, relator, número do processo e `inteiro teor` são descartados.
- Anonimização: `ai-model/scripts/anonimizar.py` (CPF, CNPJ, e-mail, telefone, OAB, nº CNJ, linhas de partes). Cada coleta imprime uma auditoria dos identificadores restantes.
- Risco residual: nomes próprios soltos no meio de frases (sem NER).

## Como gerar

```
python ai-model/scripts/coletar_dados.py --mb 150 --saida datasets/ementas.csv
```

Só usa a biblioteca padrão do Python e lê os arquivos por streaming (não baixa os 500 MB inteiros). Arquivos acima de 50 MB ficam fora do GitHub.
