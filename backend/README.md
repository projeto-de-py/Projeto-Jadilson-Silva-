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
| POST | `/api/auth/login` | público | Login (email + senha) → JWT |
| GET | `/api/auth/me` | autenticado | Dados do usuário logado |
| GET | `/api/usuarios` | **Admin** | Lista usuários |
| POST | `/api/usuarios` | **Admin** | Cadastra usuário (ADMIN ou PADRAO) |

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
python main.py
```

> **AppLocker bloqueia `alembic.exe`?** Use o comando do passo 4 (`python -c ...`) como alternativa.

### Credenciais do seed (troque após o 1º login)

```
e-mail: admin@jadilson.adv
senha : Admin@123
```

### Teste rápido do login

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/login `
  -ContentType 'application/json' `
  -Body '{"email":"admin@jadilson.adv","senha":"Admin@123"}'
```

## Segurança implementada

- Senha com **bcrypt** (nunca em texto puro — RNF01)
- **JWT** HS256 com expiração de 8h (`JWT_EXPIRE_MINUTES`)
- Resposta **genérica** em login inválido (não revela se o email existe)
- Usuário inativo bloqueado com 403
- Permissões **sempre no servidor**: `require_admin` protege rotas Admin (RF02/RF07/RF08)
- CORS liberado apenas para o frontend Vite (`localhost:5173`)

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
