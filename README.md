# Sistema de Gestão de Casos e Agenda — Advocacia Jadilson Silva

Projeto com **backend FastAPI + SQLAlchemy + MySQL** (autenticação JWT em cookie HttpOnly com CSRF, rate limit e autorização por perfil) e **frontend React + Vite + Tailwind CSS**. A API segue arquitetura em camadas (routes → services → repositories → models). Instruções detalhadas da API: [`backend/README.md`](backend/README.md).

## Dependências e configuração

Execute a partir da raiz do repositório. Use Python 3.14 e Node 22.12 ou superior; se o ambiente virtual já existir, preserve-o.

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements-lock.txt
cd frontend/frontend-jadilson
npm ci
cd ../..
```

No Windows (PowerShell):

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-lock.txt
cd frontend\frontend-jadilson
npm install
cd ..\..
```

## Preparação do banco (MySQL)

```bash
mysql -u root -p -e "CREATE DATABASE advocacia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Crie o arquivo de configuração do backend (não versionado) a partir do template e ajuste `DATABASE_URL` (usuário/senha do MySQL) e gere um `JWT_SECRET` forte:

```bash
cd backend
copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"   # valor para JWT_SECRET
```

## Migrações e usuário inicial

```bash
cd backend
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1

# cria/atualiza as tabelas via Alembic (AppLocker bloqueia alembic.exe? use este formato)
python -c "from alembic.config import main; main(['upgrade','head'])"

# cria o administrador inicial (idempotente)
python -m app.seed
```

**Login inicial (seed):** `admin@jadilson.adv` — a senha é **gerada aleatoriamente e impressa no terminal** pelo `python -m app.seed` (ou defina `ADMIN_SENHA_INICIAL` no `.env`). Troque após o 1º acesso.

### Situação das migrações (26/11/2026)

Cadeia versionada: `0001` (usuários) → `0002` (casos/prazos) → `0003` (Fase 1) →
`0004` (Fase 2) → `0005` (Fase 3) → `0006` (Fase 4) → `0007` (permissão de
compromissos) → `0009` (uso de IA) → `0010` (financeiro/assinaturas) → `0011`
(eventos de agenda) → `0012` (notificações) → `0013` (configurações do
escritório) → `0014` (origem dos andamentos) → **`0015` (documentos no banco)** — head atual.

**Banco MySQL `advocacia` em dia desde 26/11/2026:** a base foi criada/ atualizada
com **a cadeia completa até `0015`**, e `alembic check` confirmou **sem
divergências entre models e migrations** no MySQL (20 tabelas). A cadeia também foi
**validada em SQLite descartável** (upgrade → downgrade → re-upgrade) e em
`tests/test_migracoes.py`.

Para qualquer atualização futura de schema, **só execute com backup e autorização
do time**:

```bash
# 1) backup (ajuste usuário/senha; NUNCA commite o arquivo gerado)
mysqldump -u root -p advocacia > backup_advocacia_antes_upgrade.sql

# 2) revisão aplicada NO banco (deve imprimir 0015_documentos; se
#    imprimir outra coisa, o banco está atrás do repositório)
python -c "from alembic.config import main; main(['current'])"

# 3) em caso de dúvida, confirme direto no banco (somente leitura)
#    SELECT * FROM advocacia.alembic_version;

# 4) upgrade (só com autorização do time)
python -c "from alembic.config import main; main(['upgrade','head'])"
```

## Iniciar o sistema

Terminal do backend:

```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Documentação interativa: `http://127.0.0.1:8000/docs` (desativada em produção com `APP_ENV=production`).

Em outro terminal, a partir da raiz:

```bash
cd frontend/frontend-jadilson
npm run dev
```

Abra `http://127.0.0.1:5173`. O Vite encaminha `/api` para `127.0.0.1:8000`, então o frontend fala com a API pela mesma origem (o cookie de sessão funciona sem CORS em desenvolvimento).

## Verificação

```bash
cd backend
source .venv/bin/activate
python -m pytest          # 641 testes (unit + API + Fases 1-7 + migrations) — SQLite em memória, sem tocar o MySQL
```

Suíte executada em **26/11/2026: 641 testes aprovados, 1 ignorado (NER sem
scikit-learn instalado), 0 falhas**.
Detalhes em [`backend/README.md`](backend/README.md).

```bash
cd frontend/frontend-jadilson
npm run build             # build de produção
npm run lint              # ESLint (0 erros)
```

## Documentação

| Documento | Conteúdo |
|---|---|
| [`backend/README.md`](backend/README.md) | API: arquitetura, endpoints, banco e testes |
| [`docs/CONTEXTO_IA.md`](docs/CONTEXTO_IA.md) | Handoff completo do projeto (status dos RFs, roadmap) |
| [`docs/FASE1_CADASTROS.md`](docs/FASE1_CADASTROS.md) … [`docs/FASE4_PRAZOS_COMPROMISSOS.md`](docs/FASE4_PRAZOS_COMPROMISSOS.md) | Documentação técnica por fase |
| [`docs/SOBRE_O_APP.md`](docs/SOBRE_O_APP.md), [`docs/ARQUITETURA_INTEGRACOES.md`](docs/ARQUITETURA_INTEGRACOES.md) | Visão geral e integrações externas |
| [`docs/ROTEIRO_PRE_ENTREGA.md`](docs/ROTEIRO_PRE_ENTREGA.md) | Roteiro de demonstração passo a passo |

> **Frontend — escopo real:** a **autenticação é contra a API real**
> (login/sessão/logout pelo proxy `/api`) e, desde as Fases 5–7, **todas as
> telas do dashboard consomem a API real** (dashboard, processos, prazos,
> agenda, clientes, andamentos, notificações, financeiro, configurações).
> **Documentos** também passaram a usar a API real (`/api/documentos`), com o
> conteúdo no banco e escopo pelo caso; as **pastas personalizadas** seguem no
> navegador. A IA usa lista de prazos estática — descrita em
> [`docs/ROTEIRO_PRE_ENTREGA.md`](docs/ROTEIRO_PRE_ENTREGA.md).

## Sessões e produção futura

O login entrega um **JWT (HS256, 8h)** em cookie `HttpOnly` + `SameSite`; o JavaScript não acessa o token. O `logout` revoga o `jti` no servidor, então um token roubado deixa de valer. Todo `POST/PUT/PATCH/DELETE` sob `/api` exige o header `X-CSRF-Token` (claim embutido no JWT). Rate limit de login: 5 falhas por e-mail e 20 por IP a cada 5 minutos.

Para produção futura: `APP_ENV=production` (a API aborta o startup se `JWT_SECRET` for fraco, cookie sem `Secure` ou CORS com curinga e desativa `/docs`), `AUTH_COOKIE_SECURE=true` (HTTPS), origem real em `CORS_ORIGINS` (nunca `*`), nginx à frente do uvicorn e um único worker (rate limit e blocklist de tokens moram em memória).

## Estrutura do projeto

```
backend/
  app/                 # API em camadas
    api/               # rotas + dependências (get_current_user, require_admin)
    services/          # regras de negócio (auth, usuários)
    repositories/      # todo SQL mora aqui
    models/            # tabelas SQLAlchemy
    schemas/           # contratos de entrada/saída (Pydantic)
    core/              # security (bcrypt + JWT), ratelimit, revogação de tokens
    main.py            # fábrica create_app (CORS, middleware, routers)
    config.py          # Settings (pydantic-settings, lê .env)
    seed.py            # administrador inicial (idempotente)
  alembic/             # migrações
  tests/               # pytest (SQLite em memória via dependency_overrides)
frontend/frontend-jadilson/   # React + Vite + Tailwind
docs/                  # documentação (CONTEXTO_IA.md, DER, etc.)
```
