# CONTEXTO COMPLETO DO PROJETO — documento de handoff para IA

> **Como usar:** cole este documento (ou anexe-o) como primeira mensagem da próxima
> sessão de IA. Ele foi escrito em **16/10/2026** e reflete o estado real do código.
> Seções 8 e 14 contêm os pontos críticos (conflito de sistemas e próximos passos).

> ⚠️ **STATUS ATUAL (atualizado nesta auditoria de segurança):** a árvore de código
> contém **apenas o Sistema A** (`backend/app/`, arquitetura em camadas, JWT em cookie
> HttpOnly + CSRF + rate limit + revogação de sessão). O **"Sistema B"** descrito nas
> seções 7, 8 e 11 (scripts na raiz de `backend/`, `src/lib/api.js`, etc.) **não está
> presente localmente** — essas seções estão **desatualizadas** e descrevem um estado
> que não existe mais no working tree. O frontend usa `AuthProvider` + `api/client.js`
> (Sistema A). Não siga as instruções do Sistema B sem confirmar o conteúdo atual dos
> arquivos.

---

## 1. Identidade do projeto

- **Nome:** Sistema de Gestão de Casos e Agenda Inteligente para Escritório de Advocacia
- **Natureza:** Projeto de Extensão — Engenharia de Software, **UniRios** (Centro Universitário do Rio São Francisco), Paulo Afonso/Delmiro Gouveia – BA, 2026
- **Cliente/fictício:** escritório "Jadilson Silva Adv."
- **Equipe (5):** Guilherme Sant'Ana, Rubens Alves, **Vinicius Teixeira**, **Natalino Varela (líder)**, Antonio Gomes
- **Repositório:** `https://github.com/projeto-de-py/Projeto-Jadilson-Silva-` (organização GitHub `projeto-de-py`, branch `main`)
- **Documento oficial de requisitos (fonte da verdade):** PDF "Vinicius teixeira documentacao inicial (1).pdf" (em `C:\Users\vinic\Downloads\`), 8 páginas, contém: introdução, objetivos, RFs/RNFs, DER, UML de classes e casos de uso.

### Requisitos funcionais (resumo executivo)

| Código | Requisito | Status em 16/10/2026 |
|---|---|---|
| RF01 | Login por e-mail/senha | ✅ implementado (duas vezes — ver §8) |
| RF02 | Perfis Admin (advogado principal) e Padrão | ✅ backend (Sistema A) / parcial no B |
| RF03 | Padrão vê apenas casos atribuídos | ❌ próximo passo |
| RF04 | Admin vê todos os casos | ❌ próximo passo |
| RF05 | Autenticado cadastra caso | ❌ |
| RF06 | Autenticado registra andamentos | ❌ |
| RF07 | Somente Admin edita caso | ❌ |
| RF08 | Somente Admin exclui caso | ❌ |
| RF09 | Filtros (status, tipo, responsável, nº processo, cliente) | ❌ |
| RF10 | Agenda de prazos do usuário | ❌ (tela placeholder existe no dashboard) |
| RF11 | Destacar prazos vencidos/próximos | ❌ |

**RNFs relevantes:** RNF01 senha com hash (bcrypt ✅), RNF03 desempenho com centenas de registros (paginação/índices), **RNF04 front React+Vite, back Python+FastAPI**, RNF05 sem integração externa nesta etapa, RNF06 web puro.

### Modelo de dados (DER do PDF — 7 entidades)

`USUARIO` (id, nome, email, senha_hash, perfil) · `CASO` (nº processo, cliente, tipo ação, status, descrição, data criação) · `CASO_USUARIO` (N:N com data_atribuicao) · `ANDAMENTO` (histórico por caso + autor + data) · `PRAZO` (vencimento, descrição, status) · `NOTIFICACAO` (mensagem, lida, data) · `AUDITORIA` (usuário, ação, tabela, registro, data, detalhes).

⚠️ **Convenção decidida:** tabela real no MySQL chama-se **`usuarios` (plural)** — o DER diz USUARIO, mas o time renomeou e **decisão oficial (12/10) foi manter o plural**. Model, migração Alembic e seed já usam `usuarios`.

---

## 2. Stack e ambiente de desenvolvimento

| Item | Valor |
|---|---|
| Backend | Python 3.14.8, FastAPI, SQLAlchemy 2.0 (declarativo), Pydantic v2, PyJWT, bcrypt, Alembic, PyMySQL (**Sistema A**) / mysql-connector-python (**Sistema B**) |
| Frontend | React 19, Vite 8, Tailwind CSS 4 (design tokens próprios), react-router-dom 7, motion, symbols-react + Radix UI, react-query, zod, react-hook-form, recharts, prettier, eslint |
| Banco | **MySQL80** serviço Windows, porta 3306, database **`advocacia`**, InnoDB/utf8mb4. Credenciais no `backend/.env` (NUNCA commitar) |
| Portas | API **8000**, Vite **5173 (strictPort: true** — recusa outra porta**)** com **proxy `/api` → `http://127.0.0.1:8000`** |
| Caminho | `C:\Users\vinic\OneDrive\Documentos\python\projeto_adivocacia\Projeto-Jadilson-Silva-\` (dentro do **OneDrive** — sincronização pode atrasar watchers de arquivo) |
| Pythons | **Dois:** Python 3.14 do sistema (sem venv) e **`.venv`** criada pelo time dentro de `backend\` (o time roda com `.venv\Scripts\python.exe`) |
| Git/GitHub | credential manager do Windows; conta `ViniciussFerr` é colaboradora (convite aceito em 12/10); `git push` direto no `main` funciona |

### Armadilhas do ambiente (já vividas)

1. **AppLocker bloqueia `alembic.exe`** → rodar: `python -c "from alembic.config import main; main(['upgrade','head'])"` (e `main(['stamp','head'])` para registrar sem executar).
2. **PowerShell** não aceita `&&` nem strings multilinha complexas → usar `;` e scripts `.py` temporários.
3. **Vite "fantasma":** sempre que a porta 5173 estiver ocupada, um Vite antigo (com cache de módulos velhos) pode estar servindo código velho → `taskkill` em tudo das portas 5173/8000 e subir de novo. Sintoma: código correto no arquivo mas a página roda versão antiga.
4. `pip` não existia (instalado via `python -m ensurepip`).
5. Senha real do MySQL = está em `backend/.env` (local). `.gitignore` de `backend/` cobre `.env`, `.venv/`, `__pycache__/`, `*.db`. **Nunca commitar segredo** (já passamos por isso: `.env.example` foi sanitizado).

---

## 3. Estrutura do repositório

```
Projeto-Jadilson-Silva-/
├── README.md                     # README raiz (home do GitHub): stack, como rodar
├── docs/
│   ├── projeto                   # placeholder de 1 linha
│   └── CONTEXTO_IA.md            # ESTE documento
├── backend/
│   ├── main.py                   # ⚠️ HOJE é o app do Sistema B (ver §8)
│   ├── app/                      # ✅ SISTEMA A — arquitetura em camadas (ver §6)
│   │   ├── main.py               #   fábrica create_app + CORS + routers
│   │   ├── config.py             #   Settings pydantic-settings (.env)
│   │   ├── database.py           #   engine MySQL (pool_pre_ping), Base, get_db
│   │   ├── seed.py               #   cria tabela (fallback) + Admin (idempotente)
│   │   ├── core/security.py      #   bcrypt hash + JWT criar/decodificar
│   │   ├── models/usuario.py     #   tabela `usuarios` + enum Perfil (ADMIN|PADRAO)
│   │   ├── schemas/              #   DTOs: auth.py, usuario.py (...Out nunca vaza hash)
│   │   ├── repositories/         #   UsuarioRepository (todo SQL mora aqui)
│   │   ├── services/             #   AuthService (login), UsuarioService (cadastro)
│   │   └── api/                  #   deps.py (get_current_user, require_admin) + routes/
│   │       └── routes/{auth,usuarios}.py
│   ├── alembic/                  # migrações (versions/0001_cria_tabela_usuario.py → tabela `usuarios`)
│   ├── .env                      # LOCAL: DATABASE_URL, JWT_SECRET, CORS (não versionado)
│   ├── .env.example              # template com placeholders
│   ├── requirements.txt / requirements-dev.txt / requirements-lock.txt
│   ├── README.md                 # instruções da API
│   ├── auth.py, config.py, database.py, criar_usuario.py   # ⚠️ SISTEMA B (raiz)
│   ├── banco/                    # ⚠️ scripts SQL + preparação do Sistema B
│   └── tests/                    # ⚠️ testes do Sistema B (unit + integração MySQL)
└── frontend/frontend-jadilson/
    ├── vite.config.js            # alias @→src, proxy /api→8000, strictPort 5173
    ├── jsconfig.json             # paths p/ editor
    ├── index.html                # título "Jadilson Silva Adv."
    └── src/
        ├── main.jsx              # root React (StrictMode)
        ├── App.jsx               # ⚠️ roteamento + fluxo de login ativo (ver §8)
        ├── index.css             # @theme Tailwind (tokens de cor)
        ├── styles/               # globals.css + tokens.css (do design system)
        ├── lib/api.js            # ⚠️ client HTTP do Sistema B (cookies + CSRF)
        ├── lib/{cn,motion}.js    # cn = tailwind-merge/clsx; helpers de motion
        ├── api/client.js         # ✅ client HTTP do Sistema A (JWT Bearer) — órfão hoje
        ├── context/auth-context.js + AuthProvider.jsx   # ✅ contexto JWT (Sistema A) — órfão hoje
        ├── app/layouts/DashboardLayout.jsx + app/navigation.js   # layout do dashboard
        ├── components/layout/{Sidebar,Topbar}.jsx
        ├── components/ui/        # ~24 componentes: Button, Input, Table, Modal, Tabs,
        │                         # Toast, Tooltip, Select, Pagination, Skeleton, ...
        │                         # index.js (barrel) + toastContext.js
        ├── hooks/useToast.js
        ├── pages/
        │   ├── Login/AuthPage.jsx        # tela de login (design + integração ativa)
        │   ├── DesignSystem/DesignSystemPage.jsx  # galeria de componentes (/design-system)
        │   └── DashBoard/{Home,Processos,Prazos,Agenda,Clientes,Configuracoes}/  # telas
        └── assets/images/        # Logo_Jadilson.png, favicon.ico
```

---

## 4. Padrões de projeto aplicados (inventário com localização)

| Padrão | Onde | Para quê |
|---|---|---|
| **Arquitetura em camadas (Layered)** | `backend/app/`: routes → services → repositories → models | Separar HTTP de regra de negócio de SQL (RNF04) |
| **Repository** | `app/repositories/usuario_repository.py` | Todo SQL isolado; trocar banco/testar sem tocar regras |
| **Service Layer** | `app/services/{auth,usuario}_service.py` | Regras: credenciais, permissões, validações |
| **DTO / Adapter (Pydantic)** | `app/schemas/` (`UsuarioOut`, `LoginRequest`) | Contrato de API ≠ modelo do banco; nunca expõe `senha_hash` |
| **Dependency Injection** | FastAPI `Depends`: `get_db`, `get_usuario_repo`, `get_current_user`, `require_admin` | Injetar sessão, usuário JWT e permissões |
| **Guard de perfil** | `app/api/deps.py → require_admin` | Autorização **sempre no servidor** (RF02/RF07/RF08) |
| **Factory** | `app/main.py → create_app()`, `Sistema B main.py → create_app()` | App configurável/testável |
| **Facade** | `frontend/src/api/client.js` (A) e `src/lib/api.js` (B) | Ponto único de HTTP; nenhum `fetch` solto em componente |
| **Context (State)** | `src/context/AuthProvider.jsx` + `auth-context.js` | Sessão JWT global, `login/logout`, persistência em `localStorage` |
| **Guard / Protected Route** | `App.jsx`: `Protegida` e `LoginOuRedirect` (A) · gate por `session` (B) | Rotas privadas; redireciona para `/` sem sessão |
| **Separation of concerns (arquivos)** | `auth-context.js` (só contexto/hook) separado de `AuthProvider.jsx` (só componente) | Evita erro `react-refresh/only-export-components` |
| **Design System / Compound UI** | `components/ui/` com barrel `index.js` | Reuso e consistência visual |
| **Estratégia prevista (Fase 2)** | N/A ainda — planejado em `services/visibilidade.py` | Strategy: `AdminVêTodos` vs `PadraoVêAtribuidos` (RF03/RF04) |
| **Ports & Adapters (futuro MinutaIA)** | Planejado: `core/minuta_provider.py` (Protocol) + adapters mock/openai/ollama | Trocar provedor de IA sem tocar em regra (ver §14) |
| **Observer-lite / eventos (futuro)** | Planejado `eventbus.py` simples | Desacoplar notificações/minutaIA dos services |
| **Background Job (futuro)** | FastAPI `BackgroundTasks` + polling de job | Geração de minuta não bloqueia request |

---

## 5. Nomenclatura e convenções do time

- **Domínio em português:** entidades e termos de negócio em PT (`Usuario`, `Caso`, `Prazo`, `Andamento`, `Perfil`, `criado_em`, `senha_hash`). Inglês só para utilidades genéricas.
- **Backend:**
  - pastas/arquivos `snake_case` (`usuario_repository.py`), classes `PascalCase` (`UsuarioRepository`), funções/variáveis `snake_case`.
  - rotas REST em `/api/...` (`/api/auth/login`, `/api/usuarios`).
  - schemas de saída sufixo **`Out`** (`UsuarioOut`); erro de negócio = `class XError(Exception)` no service, traduzida para `HTTPException` na rota.
  - mensagens de erro **em PT sem acento** no Sistema A (ex.: "E-mail ou senha invalidos") — Sistema B usa com acento ("E-mail ou senha inválidos.").
- **Frontend:**
  - componentes/páginas `PascalCase.jsx` (`AuthPage.jsx`, `Sidebar.jsx`); não-componentes `kebab-case.js` (`auth-context.js`, `lib/api.js`).
  - páginas em `pages/<Pagina>/<Pagina>.jsx`; pastas de página do dashboard em `pages/DashBoard/...` (⚠️ grafia **`DashBoard` com B maiúsculo** — invariante, não renomear sem revisar imports).
  - alias `@` → `src/` em imports (`@/components/ui/Button`).
  - hooks `useX` em `hooks/`; contexto `x-context.js` + `XProvider.jsx`.
- **Commits (Conventional Commits em inglês + corpo PT):** `feat:`, `fix:`, `chore:` — exemplos reais: `feat: backend de autenticacao (FastAPI + JWT + MySQL) e login conectado ao frontend`.
- **Branches:** padrão `integracao/<tema>` (ex.: `integracao/mysql-autenticacao`); trabalho direto no `main` também ocorre (recomendado: PR).

---

## 6. Backend Sistema A (`backend/app/`) — arquitetura detalhada

**Filosofia:** cada request percorre `Router (HTTP/status/DI) → Service (regras) → Repository (SQL) → MySQL`, com Pydantic na borda.

### Fluxo do login (RF01)

```
POST /api/auth/login  {email, senha}
  → routes/auth.py :: login()            # valida formato (Pydantic), 401 em ErroAutenticacao
  → services/auth_service.py :: autenticar()
       email normalizado (strip+lower)
       repo.buscar_por_email()
       security.verificar_senha()  (bcrypt.checkpw)   # mensagem genérica p/ não vazar existência
       bloqueia inativo (403)
  → security.criar_token(sub=id, perfil, exp=8h)      # JWT HS256 (PyJWT)
  → TokenResponse {access_token, token_type, usuario: UsuarioOut}
```

### Endpoints (Sistema A)

| Método | Rota | Acesso | Observação |
|---|---|---|---|
| GET | `/health` | público | status da API |
| POST | `/api/auth/login` | público | retorna JWT + usuário |
| GET | `/api/auth/me` | JWT Bearer | valida sessão (o front A chamava isto) |
| GET | `/api/usuarios` | Admin | lista usuários (RF02) |
| POST | `/api/usuarios` | Admin | cadastra (ADMIN ou PADRAO) |

### Segurança (Sistema A)

- Senha: **bcrypt** (`hash_senha`/`verificar_senha` em `core/security.py`), custo padrão.
- Token: **JWT** HS256, `JWT_SECRET` do `.env`, expiração `JWT_EXPIRE_MINUTES=480`.
- Erro de login **genérico** (não revela se email existe); inativo → 403.
- `require_admin` protege rotas; CORS restrito a `localhost:5173`.
- Seed: `python -m app.seed` → cria Admin **`admin@jadilson.adv` / `Admin@123`** (idempotente; trocar senha em produção). Seed imprime guia amigável se o MySQL recusar (erros 1045/1049/2003).

### Banco/migrações

- Tabela **`usuarios`**: `id, nome, email UNIQUE, senha_hash, perfil(10), ativo(bool), criado_em(datetime UTC)`.
- Alembic aplicado e **stamped** (`0001_cria_usuario`) no MySQL. Nova alteração de schema = `alembic revision --autogenerate` + `upgrade head` (com a trava do AppLocker, via `python -c ...`).
- Datas gravadas em **UTC sem fuso** (`utcnow()` em `models/usuario.py`) — cuidado ao exibir (UTC-3).

---

## 7. Backend Sistema B (raiz de `backend/`) — o paralelo novo

Adicionado pelo time em **`240b213 feat: integra login com MySQL e sessões`** (merge `9d7bb8a`, ~15/10). **Substituiu o conteúdo de `backend/main.py`** (nosso entrypoint uvicorn saiu).

- **Modelo de sessão, não JWT:** `POST /api/auth/login` cria sessão no banco e devolve **cookie HttpOnly (`samesite=strict`, path `/api`)** + `csrf_token` na resposta. Rotas: `/api/auth/login`, `GET /api/auth/session`, `POST /api/auth/logout` (exige header `X-CSRF-Token`).
- **Arquivos:** `auth.py` (digest/verify hash, `current_user`, `require_csrf`, `Limiter`), `config.py` (`Config.load()`), `database.py` (driver **mysql-connector**, não PyMySQL), `criar_usuario.py`, `banco/*.sql` + `preparar_autenticacao.py` + `verificacao.sql`, `tests/test_unit.py` e `tests/test_mysql_auth_real.py` (pytest), `requirements-dev.txt`, `requirements-lock.txt`.
- **Proteções extras:** rate limit (20 req/min por IP e 5/min por email no login), checagem de `Origin`, `Content-Type: application/json`, limite de 4 KB no body, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, validação de erro que **nunca ecoa a senha**.
- **Como rodar:** `uvicorn main:create_app --factory --port 8000` (o arquivo tem factory; `python main.py` sozinho não sobe nada).
- **Fronte integrado:** `src/lib/api.js` chama **relative `/api/...`** com `credentials: 'same-origin'` e header CSRF → Vite **faz proxy `/api` → `127.0.0.1:8000`**.
- `backend/.env.example` foi **esvaziado** no remoto; Sistema B lê config via `Config.load()`.

---

## 8. ⚠️ PONTO CRÍTICO — dois sistemas de autenticação coexistindo

Este é o fato **mais importante** do documento. Em 12/10 o repositório tinha **apenas** o Sistema A (JWT + camadas). Entre 12 e 16/10 o time mergeou o Sistema B por cima:

| | Sistema A (nosso) | Sistema B (do time) |
|---|---|---|
| Arquitetura | camadas (`app/`) | scripts na raiz |
| Credencial | JWT no `localStorage` | cookie HttpOnly + CSRF no banco |
| Entry | `python main.py` → `uvicorn app.main:app` | `uvicorn main:create_app --factory` |
| Driver | PyMySQL | mysql-connector |
| Testes | nenhum | pytest (unit + real MySQL) |
| Extras | escopo de perfil, seed | rate limit, CSRF, headers |

**O que está ativo HOJE no frontend (remote `main`):**
- `App.jsx` foi reescrito para usar **`session` + `api('login'|'session'|'logout')` do Sistema B** (com polling de sessão a cada 30 s e ao voltar à aba). As rotas fazem gate por `session`.
- `AuthPage.jsx` agora recebe **props** (`onLogin`, `loading`, `checking`, `error`) e usa `FormData` — o `onSubmit={handleSubmit}` do Sistema A saiu.
- `AuthProvider`, `auth-context`, `src/api/client.js` (Sistema A) continuam **no repo mas provavelmente órfãos/sem wrapper `<AuthProvider>`** — o `App.jsx` remoto ainda os importa (código morto possível → pode acusar lint).
- `backend/main.py` (entry antigo) foi **sobrescrito** pelo app do Sistema B; `backend/app/` continua intacto e funcional.

**Ação recomendada para a próxima sessão:** decidir com o time **qual sistema prevalece** e consolidar:
1. Se prevalecer **B** (tem testes + proteções): portar a autorização por perfil (RF02–RF08) para `auth.py`/services do B, reaproveitar o design de rotas do A, **remover** `AuthProvider`/`auth-context`/`api/client.js` órfãos e restaurar `.env.example`;
2. Se prevalecer **A**: rejeitar/repensar B, manter JWT, migrar as proteções valiosas de B (rate limit, CSRF/origin, headers) para o A.
3. Em qualquer caso: **um único `/api/auth/login`**, uma única tabela de sessão/usuário e docs de run atualizados (hoje `backend/README.md` e o root README descrevem o A, mas o que roda é o B).

---

## 9. Frontend — arquitetura e telas (estado atual)

- **Rotas:** `/` (login) · `/login`→`/` · `/design-system` (galeria) · layout `DashboardLayout` envolve `/home`, `/processos`, `/prazos`, `/agenda`, `/clientes`, `/configuracoes` · `*` redireciona.
- **Telas do dashboard** (`pages/DashBoard/*`): estruturas prontas com placeholder — são as telas a preencher com dados dos RFs (Processos = casos; Prazos/Agenda = RF10/RF11; Clientes/Configurações = futuros).
- **Layout:** `app/layouts/DashboardLayout.jsx` + `app/navigation.js` ( itens de menu ) + `components/layout/Sidebar.jsx` e `Topbar.jsx` (busca, notificações, avatar "JS").
- **Design system:** ~24 componentes em `components/ui/` exportados pelo barrel `index.js`; tokens de cor no `index.css` (`@theme` Tailwind: `--color-primary`, `--color-destructive`, etc.) + `styles/tokens.css`/`globals.css`. `lib/cn.js` = `clsx + tailwind-merge`.
- **Prettier** adicionado (`npm run format`); lint = `npm run lint` (**deve ficar em 0 erros**; já foi gate em integrações).
- **Validação de login no UX:** estados `loading/checking/error`, alerta com `role="alert"`, mensagem amigável por status HTTP (401/403/422/429) mapeada em `lib/api.js`.

---

## 10. Como rodar (estado em 16/10)

```powershell
# Banco (uma vez) — MySQL80 do Windows
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS advocacia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Backend — SISTEMA B (o que o front chama hoje)
cd backend
python -m pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:create_app --factory --port 8000

# Backend — SISTEMA A (alternativa/documentação)
# backend/.env com DATABASE_URL (ver .env.example), depois:
python -c "from alembic.config import main; main(['upgrade','head'])"   # AppLocker bloqueia alembic.exe
python -m app.seed                                                      # admin@jadilson.adv / Admin@123
python -c "import uvicorn; uvicorn.run('app.main:app', port=8000)"      # ou python main.py (versão antiga)

# Frontend
cd frontend/frontend-jadilson
npm install
npm run dev        # 5173 strict; proxy /api -> 8000
```

**Teste rápido:** `POST http://127.0.0.1:8000/api/auth/login` com JSON `{"email":"admin@jadilson.adv","senha":"Admin@123"}` — Sistema A devolve JSON com `access_token`; Sistema B devolve `usuario` + `csrf_token` e seta cookie.

---

## 11. Estado do Git em 16/10/2026

```
local  main  →  behind 2 de origin/main, com ALTERAÇÃO LOCAL NÃO COMMITADA:
                "D backend/.env.example" (exclusão não commitada)
remoto origin/main:
  9d7bb8a Merge branch 'integracao/mysql-autenticacao' into main
  240b213 feat: integra login com MySQL e sessões        ← Sistema B
  d6314c7 chore: remove pagina HTML estatica legada do frontend
  449b3e1 feat: backend de autenticacao (FastAPI + JWT + MySQL) e login conectado ao frontend  ← Sistema A
  ea476d6 feat: new dashboard layout and tabs            ← dashboard/colega
  052b439 feat: implement dashboard screen and new design
branch extra remota: origin/integracao/mysql-autenticacao
```

**Primeiro passo da próxima sessão (antes de codar):**
```powershell
git restore backend/.env.example      # desfaz a exclusão local
git pull --rebase origin main         # traz o Sistema B; resolve conflito do .env.example (manter o deles vazio ou regenerar com placeholders)
npm install                           # dependências podem ter mudado
npm run lint                          # conferir
```

**Histórico de integração (lição):** em 12/10 houve conflitos pesados entre nosso login e o dashboard do colega; resolvemos com `git pull --rebase` + resolução manual preservando os dois lados (App.jsx = roteamento deles + guard nosso; AuthPage = design deles + submit real nosso). Workflow recomendado agora: branches `feat/*` + Pull Request em vez de push direto no `main`.

---

## 12. Roadmap acordado (fases)

1. ~~Fase 1: fundação + login (RF01/RF02)~~ ✅ (com ressalva do §8)
2. **Fase 1.5: consolidar autenticação** (decisão A vs B, §8) — BLOQUEIA o resto
3. **Fase 2 — Casos (RF03–RF08):** tabela `casos` + `casos_usuarios` (N:N), CRUD com **Strategy de visibilidade** (`AdminVêTodos`/`PadraoVêAtribuidos`), `require_admin` em editar/excluir, **auditoria** (middleware/decorator gravando `auditoria`)
4. **Fase 3 — Busca (RF09):** filtros + paginação (RNF03: índices em `numero_processo`, `status`, `responsavel`)
5. **Fase 4 — Andamentos (RF06):** timeline no detalhe do caso
6. **Fase 5 — Agenda (RF10/RF11):** tabela `prazos`, cálculo de status (vencido ≤0 / crítico ≤3d / atenção ≤7d), telas Prazos/Agenda do dashboard
7. **Fase 6 — MinutaIA:** ver §13

### Diretriz arquitetural MinutaIA (já discutida e aceita)

- Módulo vertical `app/modules/minuta_ia/` (routes/service/models/templates) — **sem** mexer em `CasoService`.
- **Port & Adapter:** `Protocol GeradorMinuta.gerar(prompt, contexto)`; adapters `MockGerador` (primeiro, sem custo), `OpenAI`, `Ollama`; escolha via DI/`.env`.
- Tabela **`MINUTA`** no DER: `id, caso_id FK, tipo, titulo, conteudo, versao, status, created_by, created_at` (**versionamento embutido** — minuta editada vira v2).
- **Template Method** por tipo de peça (`ModeloContrato`, `Contestacao`...) registrados num registry/factory.
- Assíncrono: `BackgroundTasks` + endpoint de status de job (padrão Job/Polling); depois fila real se necessário.
- Resiliência quando sair do mock: retry (tenacity), circuit breaker, cache de prompt, auditoria de tokens.
- Eventos: `eventbus` simples hoje (alimenta notificações), amanhã dispara MinutaIA (padrão Observer).

---

## 13. Decisões já tomadas (não reabrir sem motivo)

1. **MySQL** (não Postgres/SQLite em produção) — obrigatório.
2. Tabela **`usuarios` plural** (DER diz USUARIO; time renomeou; decisão explícita 12/10).
3. Backend em **FastAPI + SQLAlchemy + Alembic** (nunca `create_all` como fonte da verdade).
4. Senhas **bcrypt**; JWT com 8h (Sistema A) / cookie session (Sistema B) — *pendente consolidar (§8)*.
5. **Autorização sempre no servidor**; front só esconde botões.
6. `.env` nunca versionado; `.env.example` com placeholders.
7. Front fala `localhost:5173` (CORS) ou proxy `/api` (Sistema B).
8. MinutaIA entra por **adapter/mock**, sem presa a provedor específico de LLM.

---

## 14. Checklist da próxima sessão de IA (ordem sugerida)

1. `git restore backend/.env.example` + `git pull --rebase origin main` + `npm install` + `npm run lint`.
2. **Levantar a questão do §8 com o time** (qual autenticação fica) — não implementar RF03+ antes disso.
3. Conferir schema real das tabelas (`SHOW TABLES`/`DESCRIBE usuarios`) — o Sistema B pode ter criado tabela de sessões e/ou coluna `atualizado_em` (o DTO deles já declara `atualizado_em`, que **não** existia no nosso DDL).
4. Só então Fase 2 (casos) seguindo as convenções da §5 e os padrões da §4.
5. Guardas de qualidade: `npm run lint` em 0 erros; testar login E2E (senha errada → alerta; certo → dashboard; rota privada sem sessão → redirect).

---
*Documento gerado em 16/10/2026 a partir da análise do código, do PDF de documentação e do histórico Git. Quando o projeto mudar, atualizar as seções 1 (status dos RFs), 8 (conflito) e 11 (Git).*
