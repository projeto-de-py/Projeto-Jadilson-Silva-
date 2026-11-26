# Relatório final de entrega — 26/11/2026

## 1. Resumo

A aplicação principal está funcional ponta a ponta, **sem IA no fluxo crítico**:
`login → cliente → caso → processo → prazo/agenda → andamento → documento`.
O MySQL `advocacia` é a fonte de verdade; o SQLite aparece apenas nos testes.
Documentos saíram do `localStorage` e passaram a ser registros do banco, com
escopo herdado do caso. Usuários e atribuição de casos têm tela própria, e as
permissões são decididas no servidor.

Fases entregues:

| Fase | Conteúdo | Commit |
|---|---|---|
| F0 | MySQL defensivo, migrations `0001`..`0015`, docs, remoção de backups versionados | `f33123a` |
| F1 | "Cadastrar Processo" cria `ProcessoJudicial` com CNJ validado (módulo 97) e checa duplicidade | `e9a327d` |
| F2 | Tela `/usuarios` (gate admin) + `ModalAcessoCaso` com 5 flags | `396815e` |
| F3 | Documentos no banco (`/api/documentos`), escopo por caso, contrato do hook preservado | `277f624` |
| F4 | Filtros RF09 no servidor (`useConsultaPaginada`) + notificações gravadas por evento e varredura | `d3101e1` |
| F5 | CI, higiene de dependências/código morto, code splitting e documentação final | `3b75d26` / `8187a1e` |
| F6 | Higiene final, smoke MySQL versionado, E2E do fluxo, testes de query params, correção do editor e fechamento da entrega | `83ec6ff` (docs alinhados em commit separado) |

## 2. O que mudou em F4/F5/F6

- **Filtros no banco:** `src/data/queryString.js` concentra a montagem dos query
  params; `src/data/consulta.js` envia `q`, `status` e demais filtros em
  Processos, Prazos e Clientes. A paginação acontece no servidor; as telas não
  filtram mais só os primeiros 100 registros.
- **Notificações independentes da tela:** a escrita de prazo dispara
  `sincronizar_notificacoes_para_todos(..., somente_prazos=True)` na mesma
  sessão da request; além disso, uma tarefa no `lifespan` do FastAPI varre os
  geradores a cada `NOTIFICACOES_VARREDURA_MINUTOS` (padrão 5; `0` desliga).
  A chave de dedupe (`prazo:<id>:<data>:<marco>`) torna a rotina idempotente.
- **Bug corrigido no editor:** o debounce de salvamento não envia mais
  `titulo=""` em `PATCH /api/documentos` (antes gerava 422). Na varredura final
  também foi corrigido o acesso direto a `/documentos/:id`: a URL (string) era
  comparada com `doc.id` (número) e redirecionava para a lista; além disso, o
  editor agora aguarda o carregamento da API antes de decidir pelo redirect.
- **Higiene de API/testes:** `HTTP_422_UNPROCESSABLE_ENTITY` (deprecado) foi
  substituído por `HTTP_422_UNPROCESSABLE_CONTENT` em 15 pontos de 9 arquivos de
  rotas; a chave JWT fraca usada no teste de assinatura falsa foi trocada por uma
  chave com ≥32 bytes.
- **E2E versionada:** `backend/tests/test_fluxo_completo.py` cobre, em SQLite,
  `login → cliente → caso → processo → prazo → agenda → andamento → documento`,
  filtros RF09 e aviso gravado no evento de escrita (sem abrir notificações).
- **Smoke MySQL versionado:** `backend/scripts/smoke_mysql.py` roda contra a API
  real, gera CNJ válido por módulo 97, usa JWT local quando `ADMIN_SENHA` não
  está exportada, confere os filtros no banco e apaga apenas o que criou
  (`--manter` preserva a massa). Nenhuma senha é gravada em arquivo versionado.
- **CI:** `.github/workflows/ci.yml` roda backend (pytest em SQLite, Python
  3.12, `requirements-lock.txt`) e frontend (`npm test`, lint e build, Node 22,
  `npm ci`).
- **Higiene anterior:** `backend/requirements.txt` reescrito em UTF-8 com as
  versões testadas; `requirements-lock.txt` inclui a transitiva
  `opentelemetry-api`. Removidos `src/api/client.js`,
  `src/context/AuthProvider.jsx` e `src/context/auth-context.js` (código morto
  confirmado por `grep` de imports).
- **Performance:** `manualChunks` no Vite separa editor, PDF, DOCX, charts,
  Radix, Motion e vendor React. O chunk principal caiu de ~1,7 MB para
  ~396 kB; o único bloco acima de 500 kB é o `html2pdf`, carregado sob demanda.

## 3. Gates executados

| Gate | Resultado |
|---|---|
| `python -m pytest -q` (suíte completa) | **651 passed, 1 skipped, 0 failed** (E2E incluso; NER sem `scikit-learn`) |
| `python -m pytest tests/test_fluxo_completo.py tests/test_unit.py -q` | **43 passed**, 2 avisos conhecidos |
| `npm test` (`node --test`) | **3 passed, 0 failed** (query params RF09) |
| `npm.cmd run lint` | 0 erros |
| `npm.cmd run build` | OK — chunks separados, sem avisos de tamanho |
| `alembic current` / `alembic check` | `0015_documentos (head)` / "No new upgrade operations detected" |
| OpenAPI | 67 caminhos / 89 operações |
| `python -m scripts.smoke_mysql` | `OK: cliente=6 caso=8 processo=5 prazo=5 andamento=5 documento=5 aviso=16; filtros no banco conferidos`; limpeza confirmada (contagens voltaram ao original) |
| Navegador | `/home`, `/processos`, `/prazos`, `/clientes`, `/documentos`, `/documentos/:id`, `/usuarios`, `/agenda`, `/financeiro`, `/configuracoes`, `/design-system` e busca global (`Ctrl+K`) sem erros de console |
| CI | YAML válido; jobs `Backend (pytest)` e `Frontend (testes + lint + build)` disparados pelo push |

A limpeza do smoke removeu somente os registros da própria execução. Após a
rodada final, o MySQL ficou com a massa pré-existente: `clientes=2`, `casos=4`,
`processos_judiciais=1`, `prazos=2`, `documentos=1`, `notificacoes=5`,
`usuarios=2`.

## 4. Como demonstrar

1. MySQL80 ativo; `alembic current` = `0015_documentos`.
2. Backend: `backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
3. Frontend: `npm.cmd run dev -- --host 127.0.0.1 --port 5173`.
4. Login: `admin@jadilson.adv` + senha do seed local (`python -m app.seed`).
5. Seguir o roteiro em `docs/ROTEIRO_PRE_ENTREGA.md` (12 passos).
6. Mutantes no Swagger exigem `X-CSRF-Token` devolvido pelo login.
7. Smoke automatizado: `.\\.venv\\Scripts\\python.exe -m scripts.smoke_mysql`
   (dentro de `backend/`; use `--manter` se quiser conservar os dados criados).

## 5. Fora do escopo / limitações

- IA real, NER e MinutaIA não participam do fluxo entregue (provedor simulado
  permanece no código, sem-modelo).
- Histórico/auditoria ampliada e integrações pagas em sandbox não foram
  estendidas nesta entrega.
- Pastas personalizadas da tela Documentos continuam em `localStorage`
  (`pastas-documentos-v1`); **documentos** e seu conteúdo estão no banco.
- Área global e PF/PJ em Clientes continuam filtradas no navegador (não há
  parâmetro equivalente no backend).
- O teste ignorado da suíte é o de NER sem `scikit-learn`; os avisos restantes
  são `StarletteDeprecationWarning` do `TestClient`/httpx e `AUTH_COOKIE_SECURE`
  em desenvolvimento.

## 6. Estado do repositório

Os commits das fases F0–F6 foram publicados em `origin/main` e o YAML da CI foi
validado. A senha do admin é local/demonstração e não está versionada
(`backend/.env` é ignorado pelo git; `ADMIN_SENHA_INICIAL` não permanece lá).
