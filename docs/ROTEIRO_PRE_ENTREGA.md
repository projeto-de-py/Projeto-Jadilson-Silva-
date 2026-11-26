# Roteiro de demonstração — pré-entrega (26/11/2026)

> Fluxo ponta a ponta **login → cliente → caso → processo → prazo/agenda →
> andamento → documento**, com MySQL real (`advocacia`) e a API como única
> fonte de verdade. Nada aqui depende de IA, `localStorage` de documentos ou
> dados fictícios já semeados: use apenas dados inventados na apresentação.

## 1. Antes de começar

| Item | Como conferir |
|---|---|
| MySQL80 | `Get-Service MySQL80` → `Running` |
| Schema | `alembic current` dentro de `backend/` → `0015_documentos`; `alembic check` → sem divergências |
| Backend | `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| Frontend | `npm.cmd run dev -- --host 127.0.0.1 --port 5173` em `frontend/frontend-jadilson` |
| Saúde | `GET http://127.0.0.1:8000/health` → `{"status":"ok","versao":"0.1.0"}` |
| Login | `admin@jadilson.adv` + senha definida localmente no seed (`python -m app.seed`) |
| Swagger | `http://127.0.0.1:8000/docs` (67 caminhos / 89 operações) |

**Mutantes** (`POST/PUT/PATCH/DELETE` sob `/api`) exigem o header
`X-CSRF-Token` com o `csrf_token` devolvido pelo login — inclusive no Swagger.
O cookie de sessão é HttpOnly; o frontend usa o proxy Vite `/api`.

> Regra da apresentação: CPF/CNPJ, nomes e e-mails **fictícios**. Evite errar
> a senha várias vezes (rate limit: 5 por e-mail / 20 por IP a cada 5 min).

## 2. Roteiro em 12 passos

| # | O que mostrar | Onde | Expectativa |
|---|---|---|---|
| 1 | API viva | `/health` e `/docs` | status `ok`, operações listadas |
| 2 | Login | frontend `/` → `/home` | Dashboard carrega; recarregar mantém a sessão (`GET /api/auth/me`) |
| 3 | Usuários | tela **Usuários** (admin) + `GET/POST/PATCH /api/usuarios` | cria usuário fictício; só admin entra na tela |
| 4 | Cliente | tela **Clientes** + `POST /api/clientes` | 201; digitar no campo de busca dispara `GET /api/clientes?q=...` (filtro no banco) |
| 5 | Caso | tela **Processos** → "Novo Processo" + `POST /api/casos` | 201 com `status=NOVO`; busca/estágio viram `?q=&status=` na API |
| 6 | Permissões | botão **Acesso ao caso** no processo + `POST /api/casos/{id}/usuarios` | 5 flags granulares; sem vínculo → 403/404 |
| 7 | Processo judicial | modal **Cadastrar Processo** + `GET /api/processos?q=<CNJ>` | CNJ validado por módulo 97, duplicidade bloqueada; busca parcial por dígitos |
| 8 | Prazo | tela **Prazos** + `POST /api/prazos`, `/concluir`, `/reabrir`, `/cancelar` | 201; `?q=` no servidor; data `inicio > vencimento` → 422 |
| 9 | Notificação do prazo | sino no Topbar (sem abrir a tela antes) | Aviso do marco já está gravado: escrita do prazo gera na hora; varredura cobre os próximos dias |
| 10 | Compromisso/agenda | tela **Agenda** + `GET /api/agenda?de=&ate=` | 201 com `AGENDADO`; `data_fim > data_inicio` obrigatório |
| 11 | Andamento | painel **Andamentos** no processo aberto | `POST /api/casos/{id}/andamentos` → trilha no caso |
| 12 | Documento | tela **Documentos** + `GET/POST/PATCH /api/documentos` | Cria, edita e move de pasta; conteúdo no MySQL, escopo pelo caso; `PATCH .../mover` preserva `atualizado_em` |

Falas curtas sugeridas: (a) "a busca não filtra só os 100 primeiros: o
query param vai para o banco"; (b) "o processo real tem CNJ validado e não
pode duplicar"; (c) "o aviso de prazo é gravado pelo servidor, não quando o
sino é aberto"; (d) "o documento saiu do navegador e virou registro do caso".

## 3. Onde cada coisa vive

| Área | Frontend | API |
|---|---|---|
| Login/sessão | integral (cookie + CSRF) | `/api/auth/login|me|logout` |
| Clientes, casos, processos, prazos | telas com filtros no servidor | `GET/POST/PATCH/DELETE` correspondentes |
| Usuários e acesso ao caso | tela Usuários + botão no processo | `/api/usuarios`, `/api/casos/{id}/usuarios` |
| Notificações | sino com polling de 15 s | `/api/notificacoes` (+ varredura no servidor) |
| Documentos | tela Documentos (pastas locais) | `/api/documentos` |
| Andamentos | painel no processo | `/api/casos/{id}/andamentos` |
| Histórico/auditoria | sem tela dedicada | endpoints `/historico` |
| MinutaIA / NER | não demonstrar | fora do escopo desta entrega |

## 4. Gate antes da apresentação

```powershell
# backend
cd backend
.\.venv\Scripts\python.exe -m pytest -q
# frontend
cd frontend\frontend-jadilson
npm.cmd run lint
npm.cmd run build
```

- [ ] `/health` responde e `/docs` abre
- [ ] `alembic current` = `0015_documentos` e `alembic check` limpo
- [ ] login admin funciona e logout revoga a sessão
- [ ] filtros de Processos/Prazos/Clientes mandam `?q=` na rede (aba Network)
- [ ] documento criado pela UI aparece em `GET /api/documentos`
- [ ] prazo criado gera aviso sem abrir o painel de notificações
- [ ] `npm.cmd run lint` sem erros e `npm.cmd run build` OK

## 5. Se algo der errado

| Sintoma | Causa provável | Contorno |
|---|---|---|
| Login 500 | migrations desatualizadas | backup → `alembic upgrade head` |
| 401 no Swagger | sessão expirada/logout | refaça `POST /api/auth/login` |
| 403 em mutação | falta `X-CSRF-Token` | use o `csrf_token` do login |
| 429 no login | rate limit | aguarde 5 min ou reinicie o backend |
| Lista vazia após filtro | termo sem correspondência | limpe o campo de busca |
| Documento some | estava em pasta local diferente | verifique a pasta na tela Documentos |
| 5173 ocupada | Vite anterior | encerre o processo antigo (porta fixa) |
