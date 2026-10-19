# Login com MySQL e sessões

O frontend React/Vite usa a API FastAPI para permitir acesso somente a pessoas cadastradas e ativas, com e-mail e senha corretos. As rotas internas exigem sessão; recarregar a página restaura a sessão, e sair a revoga no MySQL. Os estilos, animações e dados demonstrativos existentes foram preservados. Não há cadastro público, recuperação de senha ou integração das demais funcionalidades.

## Dependências e configuração

Execute a partir da raiz do repositório. Use Python 3.13 e Node 22.12 ou superior; se o ambiente virtual já existir, preserve-o.

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements-lock.txt
cd frontend/frontend-jadilson
npm ci
cd ../..
```

O MySQL 8.4 deve estar instalado e funcionando, com `bind-address=127.0.0.1`, `mysqlx-bind-address=127.0.0.1` e `general-log=0`. No Homebrew, confira `brew services list` antes de usar `brew services start mysql@8.4`. Preserve outros serviços e bancos. A compilação no macOS 12 pode exigir ajustes de compatibilidade do Homebrew; os scripts abaixo não instalam nem substituem o servidor.

## Preparação local do banco

```bash
source backend/.venv/bin/activate
python backend/banco/preparar_autenticacao.py
python backend/banco/testar_real.py
```

O preparador solicita a senha administrativa com entrada oculta (Enter para uma senha vazia em instalação nova). Usa o socket `/tmp/mysql.sock`; defina `MYSQL_ADMIN_SOCKET` se seu servidor usar outro caminho. Não passe senhas em argumentos, SQL, histórico ou mensagens.

O script prepara apenas `sistema.usuarios` e `sistema.sessoes`, com InnoDB, charset `utf8mb4` e collation `utf8mb4_unicode_ci`. Compara estruturas existentes antes de executar DDL. Se houver divergência, preserva os registros e interrompe para revisão; não apaga, recria ou migra tabelas existentes automaticamente. As demais tabelas, se existirem, permanecem preservadas.

A conta de conexão é `sistema_app@localhost`, com apenas `SELECT`, `INSERT` e `UPDATE` nas duas tabelas. Para conta nova, a senha forte é gerada em memória. Para conta existente, a credencial é verificada antes de qualquer ajuste; acessos fora do escopo interrompem a preparação para preservar outros sistemas.

As credenciais reais são gravadas em `backend/.env` com permissão `0600`. Credenciais diferentes já configuradas são preservadas para revisão. Use `backend/.env.example` como referência sem segredos. Locks, relatórios, planos de revisão e a cópia privada das credenciais ficam em `backend/.local/mysql/`, ignorada pelo Git. Os SQL em `backend/banco/` não contêm senhas reais; `preparacao.sql` é uma referência comentada, e o preparador é o fluxo recomendado para conferir estruturas antes do DDL.

`sistema_app` é a conta de conexão MySQL, não uma pessoa do portal. As senhas das pessoas são diferentes e armazenadas somente como hash Argon2id. Nenhuma pessoa ou senha padrão é criada.

## Criar pessoa e iniciar o sistema

Terminal do backend:

```bash
cd backend
source .venv/bin/activate
python criar_usuario.py
python -m uvicorn main:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers --no-access-log
```

O cadastro administrativo pede nome, e-mail, perfil (`padrao` ou `admin`) e senha com confirmação oculta. Não é um endpoint público.

Em outro terminal, a partir da raiz:

```bash
cd frontend/frontend-jadilson
npm run dev
```

Abra `http://127.0.0.1:5173` (use essa origem exata). Vite encaminha `/api` para `127.0.0.1:8000`. Entre com a pessoa cadastrada, recarregue para verificar persistência e clique em **Sair** para confirmar o retorno ao login. Se usar o Node local já preparado neste Mac, acrescente `.tools/node-v22.23.3-darwin-x64/bin` ao `PATH` antes de executar npm.

## Verificação

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/test_unit.py -q
python banco/testar_real.py
```

Se o administrador do MySQL tiver senha, use `python banco/testar_real.py --admin-password`; a entrada é oculta e passa ao teste apenas em memória. Os seis testes reais verificam conexão, estrutura, permissões mínimas, defaults, e-mail duplicado, hashes Argon2, usuários ativos, credenciais inválidas, persistência/expiração, CSRF, logout, rotação e limite de tentativas. Criam registros temporários identificáveis e removem somente seus próprios registros, inclusive sessões, usando acesso administrativo. O relatório é aprovado apenas se os seis testes e a limpeza final passarem; não registra senhas, hashes, cookies ou tokens.

```bash
cd frontend/frontend-jadilson
npm run build
npm run lint
```

**Login inicial (seed):** `admin@jadilson.adv` — a senha é **gerada aleatoriamente e impressa no terminal** pelo `python -m app.seed` (ou defina `ADMIN_SENHA_INICIAL` no `.env`). Troque após o 1º acesso.

## Sessões e produção futura

O cookie é HttpOnly/SameSite Strict, com path `/api`; somente o SHA256 do identificador aleatório fica no MySQL. O backend verifica usuário ativo, expiração e revogação em cada consulta. O frontend revalida a sessão a cada 30 segundos e ao voltar à aba. Logout só é confirmado na interface após a revogação; senha e sessão não ficam em localStorage.

Todos os POSTs exigem a origem configurada e JSON; logout também exige CSRF. Use um único worker enquanto o limite de tentativas estiver em memória. Para produção futura, configure `APP_ENV=production`, `APP_ORIGIN` com HTTPS e frontend/API na mesma origem; o cookie passa a ser Secure. Proteja o comando administrativo e os arquivos `.env`. Esta preparação não realiza deploy.
