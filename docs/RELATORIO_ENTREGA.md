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
| F5 | CI, higiene de dependências/código morto, code splitting e documentação final | ver `git log` |

## 2. O que mudou em F4/F5

- **Filtros no banco:** `src/data/consulta.js` envia `q`, `status` e demais
  filtros como query params em Processos, Prazos e Clientes. A paginação acontece
  no servidor; as telas não filtram mais só os primeiros 100 registros.
- **Notificações independentes da tela:** a escrita de prazo dispara
  `sincronizar_notificacoes_para_todos(..., somente_prazos=True)` na mesma
  sessão da request; além disso, uma tarefa no `lifespan` do FastAPI varre os
  geradores a cada `NOTIFICACOES_VARREDURA_MINUTOS` (padrão 5; `0` desliga).
  A chave de dedupe (`prazo:<id>:<data>:<marco>`) torna a rotina idempotente.
- **Bug corrigido:** o debounce de salvamento do editor não envia mais
  `titulo=""` em `PATCH /api/documentos` (antes gerava 422).
- **CI:** `.github/workflows/ci.yml` roda backend (pytest em SQLite, Python
  3.12, `requirements-lock.txt`) e frontend (lint + build, Node 22, `npm ci`).
- **Higiene:** `backend/requirements.txt` reescrito em UTF-8 com as versões
  testadas; `requirements-lock.txt` inclui a transitiva `opentelemetry-api`.
  Removidos `src/api/client.js`, `src/context/AuthProvider.jsx` e
  `src/context/auth-context.js` (código morto confirmado por `grep` de imports).
- **Performance:** `manualChunks` no Vite separa editor, PDF, DOCX, charts,
  Radix, Motion e vendor React. O chunk principal caiu de ~1,7 MB para
  ~396 kB; o único bloco acima de 500 kB é o `html2pdf`, carregado sob demanda.

## 3. Gates executados

| Gate | Resultado |
|---|---|
| `python -m pytest -q` (643 testes) | **643 passed, 1 skipped, 0 failed** (NER sem `scikit-learn`) |
| `npm.cmd run lint` | 0 erros |
| `npm.cmd run build` | OK — chunks separados, sem avisos de tamanho |
| `alembic current` / `alembic check` | `0015_documentos (head)` / "No new upgrade operations detected" |
| OpenAPI | 67 caminhos / 89 operações |
| Smoke MySQL | login → cliente → caso → prazo → filtros `?q=` (total 1) → aviso gravado antes de abrir notificações |
| Navegador | `/home`, `/processos`, `/prazos`, `/clientes`, `/documentos`, `/usuarios` sem erros de console |
| YAML do CI | válido (`backend` e `frontend`) |

## 4. Como demonstrar

1. MySQL80 ativo; `alembic current` = `0015_documentos`.
2. Backend: `backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
3. Frontend: `npm.cmd run dev -- --host 127.0.0.1 --port 5173`.
4. Login: `admin@jadilson.adv` + senha do seed local (`python -m app.seed`).
5. Seguir o roteiro em `docs/ROTEIRO_PRE_ENTREGA.md` (12 passos).
6. Mutantes no Swagger exigem `X-CSRF-Token` devolvido pelo login.

## 5. Fora do escopo / limitações

- IA real, NER e MinutaIA não participam do fluxo entregue (provedor simulado
  permanece no código, sem-modelo).
- Histórico/auditoria ampliada e integrações pagas em sandbox não foram
  estendidas nesta entrega.
- Pastas personalizadas da tela Documentos continuam em `localStorage`
  (`pastas-documentos-v1`); **documentos** e seu conteúdo estão no banco.
- Área global e PF/PJ em Clientes continuam filtradas no navegador (não há
  parâmetro equivalente no backend).

## 6. Estado do repositório

Todos os commits estão locais na branch `main`. **Nada foi pushed.** A senha do
admin é local/demonstração e não está versionada (apenas em `backend/.env`,
ignorado pelo git).
