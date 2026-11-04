# Roteiro de demonstração — Pré-entrega (05/11/2026)

> Documento da **Etapa 6** da preparação para a pré-entrega. Ele descreve apenas
> funcionalidades **realmente existentes** no sistema hoje: login contra a API
> real, CRUD completo demonstrado pelo Swagger e telas do frontend (dados de
> demonstração, quando indicado). Nada aqui foi inventado.

---

## 1. Pré-requisitos

| Item | Detalhe |
|---|---|
| Banco MySQL | `advocacia` — revisão **`0007_permissoes_compromissos`** (atualizado em 04/11/2026, após backup em `backend/.local/backup_advocacia_20261104_pre_upgrade.sql`) |
| Backend | `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` (dentro de `backend/` com o venv ativo) |
| Frontend | `npm run dev` em `frontend/frontend-jadilson` → <http://127.0.0.1:5173> |
| Swagger | <http://127.0.0.1:8000/docs> (mesma origem do backend — os cookies funcionam por lá) |
| Saúde da API | <http://127.0.0.1:8000/health> deve responder `{"status":"ok","versao":"0.1.0"}` |
| Login | `admin@jadilson.adv` + a senha do administrador (conta já existente, provisionada pelo seed) |
| Dados no banco | Seed idempotente já assegurou **6 casos fictícios e 4 prazos fictícios** além da conta admin |

**Regra de ouro durante a apresentação:** use apenas **dados fictícios**.
Não cadastre CPF/CNPJ, nomes, e-mails ou telefones de clientes reais.

**Rate limit de login:** 20 tentativas por IP a cada 5 minutos — evite
logins errados repetidos durante a demonstração.

---

## 2. Como usar o Swagger nas mutações (CSRF)

Todo `POST/PUT/PATCH/DELETE` sob `/api` exige o header **`X-CSRF-Token`**
(exceto o próprio login). O fluxo no <http://127.0.0.1:8000/docs>:

1. Abra `POST /api/auth/login` → **Try it out** → corpo de exemplo abaixo →
   **Execute**. A resposta devolve `csrf_token` e o servidor grava o cookie
   de sessão no navegador (mesma origem `127.0.0.1:8000`).
2. Nas demais mutações, informe **`X-CSRF-Token`** com o valor do
   `csrf_token` retornado pelo login (campo já documentado no OpenAPI em
   todos os POST/PUT/PATCH/DELETE).
3. As próximas requisições carregam o cookie automaticamente — não é
   preciso "Authorize" extra.

> Se a sessão expirar (8h) ou você fizer logout, refaça o passo 1.
> A documentação do header é apenas OpenAPI (adicionada em `app/main.py`);
> o comportamento de segurança da API não foi alterado.

---

## 3. Sequência da demonstração

| # | Funcionalidade | Endpoint ou tela | Dados de exemplo | Resultado esperado | Limitações |
|---|---|---|---|---|---|
| 1 | Acessar o sistema | Navegador: <http://127.0.0.1:5173> (e `/health`, `/docs` no backend) | — | Tela de login carrega; `/health` responde `{"status":"ok"}` | Backend e Vite precisam estar no ar |
| 2 | Login | Tela `/` → `POST /api/auth/login` (via `src/lib/api.js`) | `admin@jadilson.adv` + senha do admin | Dashboard abre em `/home`; sessão em cookie HttpOnly; logout revoga o token | **Única tela do frontend integrada à API** |
| 3 | Gerenciamento de usuários | **Swagger:** `GET/POST /api/usuarios`, `PATCH /api/usuarios/{id}` | `{"nome":"Marina Demonstração","email":"marina.demo@exemplo.test","senha":"Demo123456","perfil":"FUNCIONARIO"}` | 201 com o usuário criado (sem `senha_hash`); `PATCH` alterna `ativo`/`perfil` | **Sem tela no frontend** — só API. Rota exige administrador (403 para outros) |
| 4 | Cadastro e consulta de clientes | Tela `/clientes` **+ Swagger:** `GET/POST /api/clientes` | `{"nome":"Comércio Exemplo Ltda.","cpf_cnpj":"11.222.333/0001-81","email":"contato@exemplo.test","telefone":"(61) 99999-0000"}` | 201 e listagem paginada (`q`, `pagina`, `limite`); CPF/CNPJ formatado na resposta | A **tela grava em dados locais (demonstração)**; o cadastro real é pela API. Documento inválido → 422 |
| 5 | Criar e consultar um caso | Tela `/processos` (leitura demo) **+ Swagger:** `POST/GET /api/casos` | `{"titulo":"Ação de cobrança — demonstração","cliente_id":<id do cliente>,"parte_contraria":"Empresa Exemplo S.A.","area":"PREVIDENCIARIO","prioridade":"ALTA"}` | 201 com `status=NOVO`, filtros (`q`, `cliente_id`, `status`, `ordenar`, `pagina`) e `GET /api/casos/{id}` | Tela do frontend usa dados de demonstração; CRUD real pela API |
| 6 | Associação e permissões de usuários | **Swagger:** `POST/GET /api/casos/{caso_id}/usuarios`, `DELETE .../{usuario_id}` | `{"usuario_id":<id criado>,"pode_visualizar":true,"pode_gerenciar_prazos":true,"pode_gerenciar_processos":false,"pode_gerenciar_compromissos":false}` | 201 com as flags; listagem mostra quem tem acesso; usuário sem vínculo recebe 403/404 nos recursos do caso | Sem tela no frontend — só API (RF de permissões é do backend) |
| 7 | Processos judiciais do caso | Tela `/processos` (demo) **+ Swagger:** `POST/GET /api/casos/{caso_id}/processos`, `GET /api/processos?q=` | `{"numero_processo":"0000123-57.2026.8.26.0100","tribunal":"TJSP","instancia":"PRIMEIRA_INSTANCIA","status":"EM_ANDAMENTO"}` | 201 com CNJ normalizado; busca por CNJ parcial; **CNJ inválido** `0000000-00.2026.8.26.0100` → 422 | Tela usa dados de demonstração; gravação é pela API |
| 8 | Cadastrar e consultar um prazo | Tela `/prazos` (demo) **+ Swagger:** `POST/GET /api/prazos`, `PATCH .../concluir`, `.../reabrir`, `.../cancelar` | `{"caso_id":<caso>,"titulo":"Manifestação recursal — demonstração","tipo":"PROCESSUAL","data_vencimento":"2026-11-20","prioridade":"ALTA"}` | 201; filtros (`status_prazo`, `vencidos`, `prioridade`…); conclusão muda `status` para `CONCLUIDO` | Tela do frontend é demonstrativa; sem `data_inicio > data_vencimento` (422) |
| 9 | Cadastrar e consultar um compromisso | Tela `/agenda` (demo) **+ Swagger:** `POST/GET /api/compromissos`, `PATCH .../status` | `{"titulo":"Audiência de conciliação — demonstração","tipo":"AUDIENCIA","data_inicio":"2026-11-12T09:00:00","data_fim":"2026-11-12T11:00:00","caso_id":<caso>,"local":"Fórum — sala fictícia"}` | 201 (`status=AGENDADO`); `PATCH /status` aceita `REALIZADO`/`CANCELADO`; `data_fim` menor que início → 422 (CHECK + schema) | Tela do frontend é demonstrativa; gravação é pela API |
| 10 | Agenda por período | Tela `/agenda` **+ Swagger:** `GET /api/agenda?de=&ate=` | `de=2026-11-05&ate=2026-12-05` | Lista compromissos do período (padrão: hoje +30 dias); período > 366 dias → 422 | A tela exibe dados locais; a agenda real é a da API |
| 11 | Histórico e auditoria | **Swagger:** `GET /api/casos/{id}/historico`, `/api/processos/{id}/historico`, `/api/prazos/{id}/historico`, `/api/compromissos/{id}/historico` | ids criados nas etapas 5–9 | Cada alteração vira registro imutável com autor, data e detalhe (`origem`, `de`/`para`) | Sem tela dedicada no frontend — só API |

### 3.1 Roteiro narrado (resumo em 11 falas)

1. **Acessar o sistema** — abra a raiz do frontend e, em outra aba, `/health`
   e `/docs` do backend, mostrando a API viva.
2. **Login** — entre com `admin@jadilson.adv`; explique JWT em cookie
   HttpOnly + CSRF + rate limit.
3. **Usuários** — pelo Swagger, liste e cadastre um usuário fictício com
   perfil `FUNCIONARIO` (não administrador) e mostre a proteção 403 para
   quem não é administrador.
4. **Clientes** — mostre a tela `/clientes` e, no Swagger, faça o cadastro
   real e a consulta com filtro `q`.
5. **Caso** — crie um caso vinculado ao cliente recém-criado e consulte a
   listagem com filtros e paginação.
6. **Associação/permissões** — vincule o usuário do passo 3 ao caso com
   permissões granulares (`pode_visualizar`, `pode_gerenciar_prazos`…).
7. **Processos** — vincule um processo com CNJ válido ao caso; mostre a
   rejeição de um CNJ inválido (422) e a busca por CNJ.
8. **Prazo** — crie um prazo para o caso, consulte os filtros
   (`vencidos`, `status_prazo`) e conclua/reabra o prazo.
9. **Compromisso** — crie uma audiência com período válido e mude o status
   para `REALIZADO`.
10. **Agenda** — consulte `/api/agenda` no período que contém o compromisso.
11. **Histórico** — abra os quatro endpoints de histórico e mostre a trilha
    de auditoria das ações dos passos 5–9.

---

## 4. Onde demonstrar cada coisa (UI × API)

| Área | No frontend (5173) | Na API (8000/docs) |
|---|---|---|
| Login/sessão/logout | **Integral com a API real** | `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout` |
| Dashboard (`/home`), Processos, Prazos, Agenda, Clientes, Documentos, Configurações | Telas completas com **dados de demonstração locais** (`src/data/escritorio`, `localStorage`) | CRUD real correspondente |
| Usuários, Associação de usuários ao caso, Permissões, Histórico/auditoria | — (sem tela) | **Somente API** |
| Andamentos (RF06), MinutaIA, editor de documentos com IA | — | **Não existe ainda** (não demonstrar) |

---

## 5. Checklist de 2 minutos antes da apresentação

```powershell
# 1) backend (terminal 1)
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2) frontend (terminal 2)
cd frontend\frontend-jadilson
npm run dev
```

- [ ] `GET http://127.0.0.1:8000/health` → `{"status":"ok","versao":"0.1.0"}`
- [ ] `http://127.0.0.1:8000/docs` abre com os 34 caminhos
- [ ] `http://127.0.0.1:5173` abre a tela de login
- [ ] Login funcional com o administrador (sem estourar o rate limit)
- [ ] MySQL80 em execução (`Get-Service MySQL80`)
- [ ] Roteiro e este documento abertos para consulta

## 6. Possíveis imprevistos e como contornar

| Sintoma | Causa provável | Contorno |
|---|---|---|
| Login 500 | Migrations não aplicadas (banco em revisão antiga) | Ver "Situação das migrações" no `README.md` da raiz (backup → `alembic current` → `upgrade head`) |
| 401 inesperado no Swagger | Sessão expirada/logout | Refaça o login no `POST /api/auth/login` |
| 403 no Swagger | Falta o header `X-CSRF-Token` | Use o `csrf_token` devolvido pelo login |
| 429 no login | Rate limit (20/5min por IP) | Aguarde 5 minutos ou reinicie o backend (limiter é em memória) |
| Porta 5173 ocupada | Vite anterior aberto | Encerre o processo antigo (`strictPort` recusa outra porta) |
| Tela sem dados "novos" que você acabou de criar | É esperado: só login fala com a API | Consulte o dado criado no Swagger (etapas 5–9) |
