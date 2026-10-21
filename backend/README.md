# Backend - Sistema de Gestão de Casos e Agenda (Advocacia Jadilson Silva)

API **FastAPI + SQLAlchemy + MySQL** com autenticação JWT (RF01, RF02, RNF01, RNF04).

## Arquitetura (camadas)

```
HTTP → Router (api/routes) → Service (services) → Repository (repositories) → MySQL (models)
         ↑ Pydantic (DTO)       ↑ regras de negócio      ↑ SQL isolado
```

| Camada | Pasta | Responsabilidade |
|---|---|---|
| Rota | `app/api/routes/` | HTTP, status codes, dependências |
| Dependências | `app/api/deps.py` | `get_current_user` (JWT), `require_admin` |
| Service | `app/services/` | Regras: autenticação, cadastro, permissões |
| Repository | `app/repositories/` | Acesso a dados (nada de SQL fora daqui) |
| Model | `app/models/` | Tabelas SQLAlchemy |
| Schema | `app/schemas/` | Contratos de entrada/saída (DTOs) |
| Core | `app/core/security.py` | bcrypt (hash de senha) + JWT |

## Endpoints

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/health` | público | Status da API |
| POST | `/api/auth/login` | público | Login (email + senha) → cookie HttpOnly + CSRF (limite 5/email e 20/IP a cada 5 min) |
| GET | `/api/auth/me` | cookie | Dados do usuário logado + CSRF atual |
| POST | `/api/auth/logout` | cookie + CSRF | Encerra a sessão (apaga o cookie) |
| GET | `/api/usuarios` | **Admin** | Lista usuários |
| POST | `/api/usuarios` | **Admin** + CSRF | Cadastra usuário (ADMIN ou PADRAO) |

Documentação interativa: **http://127.0.0.1:8000/docs**

## Como rodar

```powershell
# 1. Dependências
python -m pip install -r requirements.txt

# 2. Configuração (ajuste usuário/senha do MySQL)
Copy-Item .env.example .env

# 3. Banco (MySQL)
mysql -u root -p -e "CREATE DATABASE advocacia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 4. Migrações
python -c "from alembic.config import main; main(['upgrade','head'])"

# 5. Usuário Admin inicial
python -m app.seed

# 6. Subir a API
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

> **AppLocker bloqueia `alembic.exe`?** Use o comando do passo 4 (`python -c ...`) como alternativa.

### Credenciais do seed

O `python -m app.seed` **nao usa senha fixa no codigo**: se voce nao definir
`ADMIN_SENHA_INICIAL` no `.env`, ele gera uma senha aleatoria forte e imprime
uma unica vez no terminal (anote-a). Troque a senha apos o primeiro login.

```
e-mail: admin@jadilson.adv
senha : (gerada e impressa pelo seed, ou a definida em ADMIN_SENHA_INICIAL)
```

### Teste rápido do login

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/login `
  -ContentType 'application/json' `
  -Body '{"email":"admin@jadilson.adv","senha":"Admin@123"}'
```

## Segurança implementada

- Senha com **bcrypt** (nunca em texto puro — RNF01)
- **JWT** HS256 com expiração de 8h (`JWT_EXPIRE_MINUTES`), entregue em **cookie HttpOnly + SameSite** (inacessível ao JavaScript — protege contra roubo de token por XSS)
- **CSRF**: todo `POST/PUT/PATCH/DELETE` sob `/api` exige o header `X-CSRF-Token` igual ao claim `csrf` embutido no JWT (verificado em `app/main.py`)
- **Revogação de sessão**: o `logout` invalida o `jti` do token no servidor (blocklist em `core/revogados.py`) — um token roubado deixa de valer assim que a vítima desloga
- **Rate limit** de login por janela deslizante (`app/core/ratelimit.py`): 5 falhas por e-mail e 20 por IP a cada 5 minutos → `429` com `Retry-After`. Falhas por e-mail só são contadas quando a senha erra (não trava quem loga certo) e o contador zera no login válido
- Resposta **genérica** em login inválido, com **tempo equalizado** (bcrypt roda mesmo com e-mail inexistente → impede enumeração por timing)
- Usuário inativo bloqueado com 403
- Headers `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` (e `Strict-Transport-Security` quando `AUTH_COOKIE_SECURE=true`)
- Permissões **sempre no servidor**: `require_admin` protege rotas Admin (RF02/RF07/RF08)
- CORS liberado apenas para as origens configuradas (`CORS_ORIGINS`) com `allow_credentials`; as respostas de erro do CSRF também recebem os headers CORS
- **Fail-fast em produção** (`APP_ENV=production`): a API aborta o startup se o `JWT_SECRET` for fraco/default, se o cookie não for `Secure` ou se houver curinga no CORS; `/docs` e `/openapi.json` ficam desativados

## Testes

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest          # 73 testes (unit + API) — rodam em SQLite em memoria
```

- `tests/test_unit.py`: bcrypt, JWT (assinatura falsa/expirada), `Limiter`, services
- `tests/test_api.py`: login, cookie HttpOnly, CSRF, rate limit, `/me`, logout, autorização Admin
- As fixtures (`tests/conftest.py`) sobrepõem `get_db` com SQLite em memoria — **nenhum teste toca no MySQL**

## Banco de dados

Tabela `usuario` (DER: USUARIO): `id, nome, email (unique), senha_hash, perfil (ADMIN|PADRAO), ativo, criado_em`.

- **Produção/desenvolvimento:** MySQL (InnoDB, utf8mb4) via `DATABASE_URL` no `.env`
- **Teste local sem MySQL:** `$env:DATABASE_URL="sqlite:///./dev.db"`
- Migrações com **Alembic** (`alembic/versions/`) — nunca alterar tabela na mão

## Próximos passos (fases)

1. Tabelas `caso`, `caso_usuario`, `andamento`, `prazo` + escopo de visibilidade (Strategy: Admin vê tudo / Padrão vê os atribuídos)
2. Filtros de busca (RF09)
3. Agenda de prazos (RF10/RF11)
4. Módulo MinutaIA (Port/Adapter com mock)
