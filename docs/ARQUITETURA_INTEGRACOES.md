# Arquitetura das integrações (APIs externas)

Este documento é para quem vai **manter** o projeto. Explica onde cada API fica, como os arquivos conversam e
como adicionar uma API nova sem bagunçar o que existe.

## 1. Visão geral

```
 React (navegador)
   │  só fala com o NOSSO backend (/api/...)
   ▼
 ROTA        app/api/routes/*.py        valida a entrada, aplica limite de uso, traduz erros em HTTP
   │
   ▼
 SERVIÇO     app/services/*.py          regra do escritório (quem pode, valores, o que gravar)
   │
   ├──▶ REPOSITÓRIO  app/repositories/*   fala com o banco (MySQL)
   │
   ▼
 CLIENTE     app/integrations/*.py      fala HTTP com UMA API externa e devolve dados tipados
   │
   ▼
 API externa (BrasilAPI, Banco Central, DataJud, ZapSign, Asaas, OpenRouter)
```

Regra de ouro: **cada camada só conhece a de baixo**. O cliente não conhece rotas nem banco; a rota não conhece
HTTP externo. Por isso dá para trocar uma API sem mexer no resto, e testar cada camada sozinha.

## 2. Mapa de arquivos

| Arquivo | Classe(s) | Papel |
|---|---|---|
| `integrations/base.py` | `ClienteHttp` | **Classe-mãe** de todo cliente: timeout, erros padronizados, cache, HTTP injetável |
| `integrations/erros.py` | `IntegracaoErro` e filhas | Único vocabulário de erro (ver §4) |
| `integrations/cache.py` | `CacheTTL` | Cache em memória com validade |
| `integrations/brasilapi.py` | `BrasilAPIClient` | Feriados, CEP, CNPJ (sem chave) |
| `integrations/bcb.py` | `BancoCentralClient`, `SerieBCB` | Taxas de juros do SGS (sem chave) |
| `integrations/datajud.py` | `NumeroCNJ`, `DataJudClient` | Valida número CNJ e consulta andamentos |
| `services/zapsign.py` | `ZapSignService` | Assinatura eletrônica (herda `ClienteHttp`) |
| `services/asaas.py` | `AsaasService` | Cobrança Pix/boleto (herda `ClienteHttp`) |
| `ia/provedores.py` | `ProvedorOpenRouter`, `ProvedorSimulado` | Modelo de IA (padrão "estratégia", ver §6) |
| `services/calendario_service.py` | `CalendarioService` | Feriados de vários anos |
| `services/juros_service.py` | `JurosService` | Compara taxa do contrato × média do Banco Central |
| `services/processo_externo_service.py` | `ProcessoExternoService` | Número CNJ → DataJud → `ConsultaProcesso` |
| `services/assinatura_service.py` | `AssinaturaService` | Valida o PDF, envia ao ZapSign, guarda e atualiza status |
| `services/financeiro_service.py` | `FinanceiroService` | Emite cobrança no Asaas, guarda parcelas, trata pagamento |
| `api/routes/consultas.py` | — | `/api/consultas/*` (feriados, CEP, CNPJ, juros, processos) |
| `api/routes/assinaturas.py`, `financeiro.py`, `webhooks.py` | — | Assinatura, cobrança e webhooks |
| `api/erros_integracao.py` | `http_de_integracao()` | Traduz `IntegracaoErro` em HTTP (um lugar só) |

No front (`frontend/.../src`): `lib/api.js` (`apiJson`, `apiIA`) faz a chamada ao nosso backend e `lib/consultas.js`
monta as consultas; as telas (`components/consultas/*`, `pages/DashBoard/Financeiro`) só usam essas funções.

## 3. Como uma chamada percorre os arquivos (exemplo: comparar juros)

1. **Tela** (`ModalCompararJuros.jsx`) chama `consultas.compararJuros(csrf, {...})` (`lib/consultas.js`).
2. `apiJson` envia `POST /api/consultas/juros/comparar` com o cookie de sessão e o token CSRF.
3. **Rota** (`consultas.comparar_juros`): o Pydantic valida o corpo (`CompararJurosIn`), `limitar_consultas`
   confere login e o teto de consultas por minuto, e chama o serviço.
4. **Serviço** (`JurosService.comparar`): valida a regra (data não futura, taxa entre 0 e 100), pede ao cliente a
   taxa média do mês, calcula diferença, razão, faixa e equivalente anual.
5. **Cliente** (`BancoCentralClient.taxa_do_mes` → `ClienteHttp._chamar_com_cache`): monta a URL do SGS, usa o
   cache (6 h), converte o JSON em `PontoSerie`.
6. A resposta sobe de volta como dataclass → schema (`ComparacaoJurosOut`) → JSON → tela.
7. Se algo falha em qualquer ponto, vira `IntegracaoErro`, e a rota o traduz com `http_de_integracao`.

## 4. Erros (hierarquia única)

| Erro | Quando | HTTP |
|---|---|---|
| `IntegracaoNaoConfiguradaError` | falta chave/token no servidor | 503 |
| `DadosInvalidosError` | entrada que não serve (CEP curto, número CNJ com dígito errado) — **nem chega a chamar a API** | 422 |
| `IntegracaoNaoEncontradaError` | o serviço externo respondeu 404 | 404 |
| `IntegracaoErro` (status 429) | limite de uso do provedor | 429 |
| `IntegracaoErro` (demais) | rede, timeout, 5xx, resposta fora do formato | 502 |

A mensagem de cada erro é **segura para exibir**: nunca leva token, cabeçalho nem o corpo bruto do provedor.

## 5. Como adicionar uma API nova (passo a passo)

1. **Cliente** em `integrations/minhaapi.py`, herdando `ClienteHttp` (veja o exemplo no topo de `base.py`):
   defina `servico`, o gancho `_cabecalhos()` (autenticação) e um método por operação, devolvendo
   **dataclasses** (não dicionários soltos).
2. **Serviço** em `services/`, com a regra do escritório, recebendo o cliente no construtor (injeção).
3. **Schema** em `schemas/` (Pydantic) para a resposta.
4. **Rota** em `api/routes/`, usando `Depends(get_current_user)`, o limite (`limitar_consultas`) e
   `http_de_integracao`. Registre em `main.py`.
5. **Config** em `config.py` (`SecretStr` para chaves) e em `.env.example`.
6. **Testes** com `httpx.MockTransport` (modelo: `tests/test_consultas.py`).

## 6. Padrões usados (para quem for ler o código)

- **Herança** (`ClienteHttp`): o comportamento comum (erros, timeout, cache) fica num lugar só.
- **Injeção de dependência**: o cliente HTTP (`http=`) e os clientes das rotas (`Depends(...)`) são trocáveis nos
  testes — por isso nenhum teste toca a internet nem usa chave real.
- **Estratégia** (`ia/provedores.py`): o serviço de IA conversa com a interface `Provedor`; `ProvedorSimulado` e
  `ProvedorOpenRouter` são intercambiáveis.
- **Repositório** (`repositories/`): o SQL fica isolado; o serviço não sabe como o banco guarda.
- **Cache com validade** (`CacheTTL`): feriados 30 dias, CEP/CNPJ 1 dia, taxas do Banco Central 6 h,
  DataJud 5 min.
- **Dataclasses imutáveis** (`frozen=True`) para os dados que saem dos clientes.

## 7. Configuração (`backend/.env`)

| Variável | Para quê | Obrigatória? |
|---|---|---|
| `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_MODELOS_ALTERNATIVOS`, `IA_PROVEDOR` | IA | só com `IA_PROVEDOR=openrouter` |
| `DATAJUD_API_KEY` | andamentos (chave **pública** do CNJ: <https://datajud-wiki.cnj.jus.br/api-publica/acesso>) | para consultar processos |
| `ZAPSIGN_API_TOKEN`, `ZAPSIGN_WEBHOOK_SECRET` | assinatura | para assinar |
| `ASAAS_API_KEY`, `ASAAS_WEBHOOK_TOKEN`, `ASAAS_API_URL` | cobrança (sandbox por padrão) | para cobrar |
| `BRASILAPI_URL`, `BCB_SGS_URL`, `CONSULTAS_LIMITE_MINUTO` | consultas públicas (já têm padrão) | não |

BrasilAPI e Banco Central **não usam chave**. Chaves ficam só no `.env` (tipo `SecretStr`) e nunca vão para log,
resposta nem para o navegador.

## 8. Limites conhecidos

- O cache vive na memória de **um** processo (com vários workers, cada um tem o seu). Para compartilhar, troque o
  `CacheTTL` por Redis mantendo os mesmos três métodos.
- **Banco Central:** `SERIES` só tem as séries cujo código foi **conferido** no catálogo oficial. Cheque especial,
  cartão rotativo e financiamento de veículos ainda **não** estão: confirme o código no catálogo e acrescente.
- **DataJud:** traz dados e movimentações, não o inteiro teor, e não mostra processos em segredo de justiça. Só
  consulta Justiça Estadual, do Trabalho, Federal e STJ.
- A comparação de juros entrega **números e uma faixa descritiva**; dizer se a taxa é abusiva é juízo do advogado.
