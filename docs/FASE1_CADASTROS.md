# FASE 1 — Cadastros e Controle de Acesso

Implementação da base de cadastro (usuários, clientes) e do controle de acesso
por caso, seguindo a arquitetura em camadas do projeto (Router → Service →
Repository → Models, com DI do FastAPI e Pydantic como DTO).

## 1. Perfis e privilégio administrativo

| Categoria | Como é identificada | Pode ver | Pode gerenciar |
|---|---|---|---|
| Advogado principal (admin) | `Usuario.perfil = ADVOGADO` **+** `Usuario.administrador = True` | todos os casos e clientes | usuários, concessões/revogações de acesso |
| Advogado colaborador | `perfil = ADVOGADO`, `administrador = False` | só casos autorizados (+ seus clientes/prazos) | nada administrativo |
| Funcionário | `perfil = FUNCIONARIO` | só casos autorizados (+ seus clientes/prazos) | nada administrativo |

Decisões importantes:

- O advogado principal **não tem perfil próprio**: é um advogado com a
  permissão administrativa adicional (`administrador`). Isso mantém os dois
  perfis funcionais pedidos (`ADVOGADO`, `FUNCIONARIO`).
- `administrador` **nunca vem de payload de API**: `UsuarioCreate` e
  `UsuarioUpdate` usam `extra="forbid"` e não declaram o campo → qualquer
  tentativa de envio responde `422`. Não há senha especial compartilhada.
- O provisionamento é feito por configuração administrativa (`ADMIN_EMAIL` no
  `.env`, default `admin@jadilson.adv`) executando `python -m app.seed`. O seed
  também **promove** a conta existente caso ela ainda não tenha a permissão
  (bancos criados antes da Fase 1). Nenhuma credencial no código: a senha vem
  de `ADMIN_SENHA_INICIAL` ou é gerada aleatoriamente e impressa uma única vez.

## 2. Models novos/alterados

### `usuarios` (alterado — `app/models/usuario.py`)

`id, nome, email (unique), senha_hash, perfil (ADVOGADO|FUNCIONARIO, String(20)),
administrador (bool), ativo, criado_em, atualizado_em`

### `clientes` (novo — `app/models/cliente.py`)

`id, nome, cpf_cnpj (String(14), anulável, unique), email, telefone,
data_nascimento, ativo, criado_em, atualizado_em`

- CPF/CNPJ **não é PK**; a coluna guarda só dígitos (11 = CPF, 14 = CNPJ).
- Política de documento ausente: `NULL` — o UNIQUE do banco ignora NULL, então
  vários clientes podem ficar sem documento; unicidade conferida (service +
  banco) apenas para documentos presentes. `""` na entrada vira `NULL`.
- Validação de dígitos verificadores em `app/core/validacao.py` (validada contra
  `python-stdnum`: 0 divergências em 1.600 documentos).
- PF e PJ no mesmo model; campos opcionais permitem expansão futura (endereço).

### `usuario_casos` (novo — `app/models/usuario_caso.py`)

`id, usuario_id (FK), caso_id (FK), pode_visualizar, pode_registrar_andamento,
pode_gerenciar_prazos, ativo, concedido_por (FK), concedido_em,
revogado_por (FK), revogado_em`

- M:N entre `usuarios` e `casos` com `UNIQUE(usuario_id, caso_id)`.
- Revogação **soft** (`ativo=False` + `revogado_por/em`): a linha permanece para
  manter a rastreabilidade de quem concedeu e quem revogou. Re-conceder reativa
  a mesma linha (não duplica — o UNIQUE impediria).
- Permissões de escrita (`pode_registrar_andamento`, `pode_gerenciar_prazos`)
  nascem `False` (menor privilégio), prontas para as próximas fases.

### `casos` (alterado — `app/models/caso.py`)

- Nova coluna `cliente_id` (FK anulável → `clientes`, `ON DELETE SET NULL`),
  ligando o caso ao cadastro. A coluna texto `cliente` foi **mantida** por
  compatibilidade com o frontend.

## 3. Regras de autorização (servidor)

A fonte única da regra de visibilidade é `app/repositories/escopo.py`:

- `condicao_caso_visivel(usuario)` — admin: todos; comum: `usuario_casos` ativas
  com `pode_visualizar`.
- `condicao_cliente_visivel(usuario)` — admin: todos; comum: clientes dos casos
  visíveis (via `casos.cliente_id`).
- `condicao_prazo_visivel(usuario)` — mesmos casos visíveis.

Códigos HTTP:

- `401` — sem sessão (ou sessão revogada/usuário desativado).
- `403` — autenticado sem privilégio (rotas Admin, CSRF ausente, auto-concessão).
- `404` — caso/cliente **inexistente ou fora do escopo** (mesmo código para os
  dois, para não revelar que o registro existe).
- `409` — conflito (e-mail/documento duplicado, concessão já ativa).
- `422` — regra de negócio (documento inválido, `administrador` no payload,
  concessão sem visualização, usuário inativo como alvo).

O gate administrativo é aplicado **uma única vez**, na dependência
`require_admin` (`app/api/deps.py`), que checa `usuario.administrador`. Os
services lançam erros de negócio que as rotas traduzem para HTTP — sem regra
de negócio no router e sem lógica de autorização duplicada.

## 4. Endpoints

| Método | Rota | Acesso | Observação |
|---|---|---|---|
| GET | `/api/usuarios` | Admin | lista usuários |
| POST | `/api/usuarios` | Admin + CSRF | cria só usuários comuns (`ADVOGADO`/`FUNCIONARIO`) |
| PATCH | `/api/usuarios/{id}` | Admin + CSRF | só aceita `ativo`/`perfil` |
| GET | `/api/casos` | cookie | lista paginada do escopo do usuário |
| GET | `/api/casos/{id}` | cookie | 404 fora do escopo |
| GET | `/api/casos/{id}/usuarios` | Admin | associações do caso (`?incluir_revogados=true` mostra o histórico) |
| POST | `/api/casos/{id}/usuarios` | Admin + CSRF | concede acesso (201); 403 auto-concessão; 409 duplicada |
| DELETE | `/api/casos/{id}/usuarios/{usuario_id}` | Admin + CSRF | revoga (204, soft delete) |
| GET | `/api/clientes` | cookie | Admin: todos; comum: só os dos casos autorizados |
| POST | `/api/clientes` | Admin + CSRF | cadastra (validação CPF/CNPJ + unicidade) |
| GET | `/api/clientes/{id}` | cookie | 404 fora do escopo |
| GET | `/api/prazos/urgentes` | cookie | agora restrito ao escopo do usuário |

## 5. Migration

`alembic/versions/0003_fase1_cadastros_acessos.py` (revisa `0002_casos_prazos`):

- **Upgrade**: cria `clientes` e `usuario_casos` (com FKs, UNIQUE e índices);
  adiciona `usuarios.administrador` e `usuarios.atualizado_em`; alarga `perfil`
  para `VARCHAR(20)`; converte os dados existentes **sem apagar nada**:
  `ADMIN` → `ADVOGADO` + `administrador=1`; `PADRAO` → `ADVOGADO`; adiciona
  `casos.cliente_id` com FK.
- **Downgrade**: remove as tabelas/colunas e reverte os perfis
  (`administrador=1` → `ADMIN`; resto → `PADRAO`).
- Migrations antigas (0001, 0002) não foram alteradas; nenhuma tabela foi
  apagada nem o banco recriado.
- Verificado em SQLite (upgrade com dados legados → downgrade → re-upgrade) e o
  SQL offline gerado para MySQL foi inspecionado (ADD COLUMN / MODIFY / FK /
  índices corretos). Teste automatizado: `tests/test_migracoes.py`.

## 6. Testes

`python -m pytest` — **146 testes passando** (executados, não declarados):

| Arquivo | Testes | Cobertura |
|---|---|---|
| `tests/test_unit.py` | 41 | bcrypt, JWT, rate limit, services |
| `tests/test_api.py` | 32 | login, cookie, CSRF, `/me`, logout, autorização Admin |
| `tests/test_fase1.py` | 47 | usuários (cadastro, duplicado, ativo/inativo, escalada), clientes (validação, duplicado, escopo), permissões (todos os casos do enunciado, HTTP real) |
| `tests/test_validacao.py` | 24 | CPF/CNPJ/telefone (unidade) |
| `tests/test_migracoes.py` | 2 | upgrade/downgrade/re-upgrade em subprocesso |

Destaque para os cenários obrigatórios cobertos em `test_fase1.py`: admin vê
todos; colaborador/funcionário veem só os autorizados; sem associação não acessa;
usuário comum não concede/revoga (403); duplicada impedida (409); trocar o id da
URL não dá acesso (404); usuário inativo não usa endpoints (401) nem loga (403);
não há como se tornar administrador pela API (422).

## 7. Compatibilidade

- O frontend só consome `/api/auth/*` (login/me/logout) e não usa `perfil`,
  `/api/casos` ou `/api/clientes` → nenhuma mudança de comportamento para ele.
- O campo `casos.cliente` (texto) continua sendo retornado nos DTOs.

## 8. Pendências / decisões futuras

- Vínculo `cliente_id` na **criação** de casos (hoje é preenchido direto no
  banco; a API de criação de casos será da próxima etapa).
- Edição/exclusão de casos (Admin) — a permissão administrativa já existe.
- Ampliar `pode_registrar_andamento`/`pode_gerenciar_prazos` quando o
  escritório definir as regras de edição.
- Endereço e demais dados cadastrais de cliente (estrutura já prevista).
- O `downgrade` não distingue `ADVOGADO` de `FUNCIONARIO` (ambos voltam para
  `PADRAO`) — perda documentada na própria migration.
