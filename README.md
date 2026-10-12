# Projeto Jadilson Silva — Sistema de Gestão de Casos e Agenda para Escritório de Advocacia

Projeto de extensão (Engenharia de Software — UniRios) para centralizar a gestão de
processos de um escritório de advocacia e controlar prazos processuais, com acesso
por perfil de usuário (Admin e Padrão).

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | React 19 + Vite + Tailwind CSS 4 |
| Backend | Python · FastAPI · SQLAlchemy 2 · Alembic |
| Banco | MySQL (InnoDB / utf8mb4) |
| Auth | JWT (PyJWT) + senha com bcrypt |

## Estrutura do repositório

```
├── backend/                  # API REST (FastAPI)
│   ├── app/
│   │   ├── api/              # rotas + dependências (JWT, require_admin)
│   │   ├── services/         # regras de negócio
│   │   ├── repositories/     # acesso a dados
│   │   ├── models/           # models SQLAlchemy
│   │   ├── schemas/          # DTOs (Pydantic)
│   │   └── core/             # segurança (bcrypt + JWT)
│   ├── alembic/              # migrações do banco
│   └── README.md             # como rodar a API
├── frontend/frontend-jadilson/   # SPA React
│   └── src/
│       ├── api/              # cliente HTTP (Facade)
│       ├── context/          # AuthProvider + useAuth
│       ├── pages/            # Login, Home
│       └── components/ui/    # Button, Input
└── docs/                     # documentação do projeto
```

## Como rodar

**1. Backend** (terminal 1):

```powershell
cd backend
python -m pip install -r requirements.txt
copy .env.example .env      # ajuste usuário/senha do MySQL
python -c "from alembic.config import main; main(['upgrade','head'])"
python -m app.seed          # cria o Admin inicial
python main.py              # http://127.0.0.1:8000/docs
```

**2. Frontend** (terminal 2):

```powershell
cd frontend\frontend-jadilson
npm install
npm run dev                 # http://localhost:5173
```

**Login inicial (seed):** `admin@jadilson.adv` / `Admin@123` — troque após o 1º acesso.

> A pasta `backend/.env` contém as credenciais locais e está no `.gitignore`;
> nunca commitar senhas.

## Funcionalidades implementadas

- ✅ RF01 — Login por e-mail e senha (JWT)
- ✅ RF02 — Perfis Admin e Padrão com proteção no servidor
- ✅ Cadastro/listagem de usuários (somente Admin)
- 🚧 Fases seguintes: casos, filtros (RF03–RF09), agenda de prazos (RF10–RF11) e módulo MinutaIA
