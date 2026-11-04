# Fase 2 — Gerenciamento de Casos Jurídicos

Evolução do sistema de gestão de escritório: cadastrar, consultar, atualizar,
arquivar e auditar casos vinculados a clientes, preservando integralmente a
Fase 1 (cadastros e controle de acesso).

## 1. Conceito central

Um **caso jurídico não é necessariamente um processo judicial**. Pode ser uma
demanda **administrativa**, **extrajudicial** ou **judicial**. Por isso:

- `numero_processo` é **opcional** (`NULL` permitido). O `UNIQUE` permanece e
  ignora NULL no MySQL/SQLite — casos sem processo não colidem.
- O caso nasce com `titulo` (identificação obrigatória em novos registros).

## 2. Modelo de dados

### `casos` (evoluído na migration `0004_casos_gestao`)

| Coluna | Tipo | Observação |
|---|---|---|
| `titulo` | VARCHAR(200), index | Obrigatório em `CasoCreate`; legado: backfill = `numero_processo` |
| `numero_processo` | VARCHAR(30), **anulável**, UNIQUE | Opcional (Fase 2) |
| `cliente` | VARCHAR(160) | Espelho de `clientes.nome` (compat. frontend) |
| `cliente_id` | FK → `clientes`, index | `ON DELETE SET NULL` |
| `area` | VARCHAR(80), index | `PREVIDENCIARIO`/`BANCARIO`/`CONSUMIDOR` na API; legados (`Civel`, `Empresarial`) continuam válidos no banco |
| `tipo_demanda` | VARCHAR(20), index | `ADMINISTRATIVA`/`EXTRAJUDICIAL`/`JUDICIAL` (default `JUDICIAL`) |
| `status` | VARCHAR(40), index | `NOVO`, `EM_ANDAMENTO`, `AGUARDANDO_CLIENTE`, `AGUARDANDO_SENTENCA`, `SUSPENSO`, `CONCLUIDO` |
| `prioridade` | VARCHAR(10) | `BAIXA`/`MEDIA`/`ALTA`/`URGENTE` (default `MEDIA`) |
| `data_abertura` | DATE, index | Default: hoje; legado: backfill `DATE(criado_em)` |
| `responsavel_id` | FK → `usuarios`, index | `ON DELETE SET NULL`; validado: ativo + perfil `ADVOGADO` |
| `observacoes` | TEXT | Opcional |
| `arquivado` | BOOL, index | Soft delete |
| `arquivado_por` / `arquivado_em` | FK / DATETIME | Rastreio do arquivamento (admin) |
| `criado_por` | FK → `usuarios` | Operador da criação |
| `atualizado_em` | DATETIME | `onupdate` automático |

### `caso_historicos` (nova)

Auditoria imutável gravada pelos services — **não existe endpoint de escrita**:

- `caso_id` (FK → `casos`, `ON DELETE CASCADE`, index), `usuario_id` (FK → `usuarios`, `SET NULL`)
- `operacao`: `CRIACAO` | `ATUALIZACAO` | `ARQUIVAMENTO`
- `dados` (JSON): apenas campos alterados, no formato
  `{"titulo": {"antes": "...", "depois": "..."}}` — nunca senhas ou tokens
- `criado_em`

## 3. Endpoints

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/api/casos` | Advogado + CSRF | Cria caso (`numero_processo` opcional) → `201` |
| GET | `/api/casos` | Cookie | Lista com filtros + ordenação + paginação no banco |
| GET | `/api/casos/arquivados` | Cookie | Lista arquivados (escopo aplicado) |
| GET | `/api/casos/{id}` | Cookie | Detalhe (`404` fora do escopo; arquivado consultável) |
| PATCH | `/api/casos/{id}` | Admin ou responsável + CSRF | Atualização parcial (`extra="forbid"`) |
| POST | `/api/casos/{id}/arquivar` | **Admin** + CSRF | Soft delete → `200`; repetido → `409` |
| GET | `/api/casos/{id}/historico` | Cookie | Auditoria (somente leitura) |

Rotas da Fase 1 preservadas: `GET/POST /api/casos/{id}/usuarios`,
`DELETE /api/casos/{id}/usuarios/{usuario_id}`.

`GET /api/casos/arquivados` é declarada **antes** de `GET /api/casos/{id}` para
não ser capturada pelo path parameter.

### Filtros e ordenação (`GET /api/casos`)

`q` (título/número/cliente/parte contrária), `cliente_id`, `area`, `status`,
`prioridade`, `responsavel_id`, `tipo_demanda`; `ordenar=abertura|prioridade`
(default `abertura` — mais recentes primeiro; `prioridade` usa ordem
URGENTE > ALTA > MEDIA > BAIXA via `CASE` no SQL); `pagina`/`limite` (máx 100).

Tudo é executado **no banco** (count + offset/limit) e sempre sob
`condicao_caso_visivel` (escopo Fase 1) + `arquivado = false`.

## 4. Regras de negócio

### Criação
1. Gate `require_advogado`: funcionário → `403`.
2. Cliente deve estar **acessível ao operador** (admin: qualquer cliente ativo;
   comum: `condicao_cliente_visivel` → inexistente/inacessível = `404`, sem vazar).
3. Cliente inativo → `422`.
4. Responsável: ativo + perfil `ADVOGADO`; inexistente/inadequado → `422`.
   Comum **só pode assumir a própria responsabilidade** (atribuir terceiros = `403`).
   Sem `responsavel_id`, o operador assume.
5. `numero_processo` duplicado (corrida) → `409`.
6. Campos administrativos no payload (`arquivado`, `criado_por`...) → `422` (`extra="forbid"`).
7. Após criar: acesso automático do responsável e do criador (`UsuarioCaso`,
   `concedido_por` = operador) — provisionamento rastreável; exceção justificada
   à proibição de auto-concessão da Fase 1 (que vale para o endpoint de gestão
   de permissões). Registro de `CRIACAO` no histórico.

### Atualização (`PATCH`)
1. Gate `require_advogado` + escopo (`404` fora do escopo).
2. Edição restrita a **admin ou responsável**; funcionário/advogado com mero
   acesso de visualização → `403`.
3. Troca de cliente repete a validação de acesso (`404`/`422`) e mantém o
   espelho `cliente` em dia.
4. Troca de responsável repete a validação (ativo + ADVOGADO) e concede o
   acesso do novo responsável.
5. `data_abertura` futura → `422`.
6. Payload sem mudanças reais → nada é gravado nem auditado.
7. Mudanças registradas em `ATUALIZACAO` com antes/depois por campo.

### Arquivamento
- Somente **admin** (`require_admin`); comum → `403`; caso inexistente/fora do
  escopo → `404`; já arquivado → `409`.
- Soft delete (`arquivado/por/em`) — **nunca há exclusão física**: prazos,
  andamentos, documentos e acessos (`usuario_casos`) permanecem intactos.
- Fora das listagens padrão; acessível por `/arquivados` (escopo) e por detalhe.
- Registrado como `ARQUIVAMENTO` no histórico.

## 5. Autorização

- **Leitura**: fonte única `app/repositories/escopo.py` (Fase 1) — admin vê
  tudo; colaborador/funcionario só o concedido. Filtros, busca, paginação e ids
  na URL não alteram isso (`404` para fora do escopo).
- **Escrita**: admin (tudo), responsável (edição do próprio caso), advogado
  (criação), admin apenas (arquivamento e gestão de permissões da Fase 1).
- Nada de autorização vinda do frontend: os DTOs não aceitam campos de
  privilégio (`extra="forbid"`) e o `administrador` jamais aparece em payload.

## 6. Migrations

`0004_casos_gestao` (revises `0003_fase1_cadastros`):

- **Upgrade**: cria `caso_historicos`; adiciona colunas em `casos` via
  `batch_alter_table` (ALTER TABLE no MySQL, recriação controlada no SQLite);
  torna `numero_processo` anulável; 6 índices novos (`titulo`, `tipo_demanda`,
  `data_abertura`, `responsavel_id`, `arquivado`, `area`); backfills
  (`titulo = numero_processo`, `data_abertura = DATE(criado_em)`).
- **Downgrade**: remove índices/colunas/tabela e restaura `NOT NULL` de
  `numero_processo` — preenchendo `NULL` com marcador reversível `'S/N-<id>'`
  (`CONCAT` no MySQL, `||` no SQLite) para não perder linhas.
- Nenhum registro apagado; migrations anteriores intocadas.

**Validação executada** (banco SQLite descartável, em `tests/test_migracoes.py`
e em verificação manual): upgrade com dados legados → conferência de colunas,
backfills, índices, UNIQUE preservado e dois casos `NULL` sem colisão →
downgrade → re-upgrade. SQL offline do MySQL inspecionado
(`alembic upgrade head --sql`).

## 7. Testes

`tests/test_fase2.py` — **52 testes**, todos verificando HTTP real:

- Criação: caso válido sem processo, casos `NULL` sem colisão, caso completo
  com processo, sem cliente/título curto (`422`), cliente inexistente/sem
  acesso (`404`), cliente inativo (`422`), funcionário (`403`), sem sessão
  (`401`), sem CSRF (`403`), responsável inexistente/inativo/não-advogado
  (`422`), comum atribuindo terceiro (`403`), acesso automático do responsável,
  processo duplicado (`409`), escalada de privilégio (`422`).
- Listagem: paginação no banco, todos os filtros, ordenação por prioridade e
  abertura, `ordenar` inválido (`422`), escopo não burlado por filtros/busca/
  ids, detalhe não autorizado (`404`), caso legado sem título.
- Atualização: admin, responsável, funcionário com acesso (`403`), advogado
  sem responsabilidade (`403`), fora do escopo (`404`), escalada (`422`),
  responsável inválido (`422`), troca de cliente com validação, data futura
  (`422`), payload sem mudança não audita.
- Arquivamento: admin (`200`) + repetido (`409`), comum (`403`), inexistente
  (`404`), sai da listagem padrão e aparece em `/arquivados`, escopo de
  arquivados, **preservação de prazos/andamentos/acessos** e detalhe
  consultável após arquivar.
- Histórico: CRIACAO/ATUALIZACAO/ARQUIVAMENTO, campos antes/depois, sem dados
  sensíveis, escopo de leitura, ausência de endpoints de escrita, autor da
  operação.

Suíte completa executada: **198 testes aprovados, 0 falhas**
(`test_unit` 41 + `test_api` 32 + `test_fase1` 47 + `test_fase2` 52 +
`test_validacao` 24 + `test_migracoes` 2).

## 8. Fora do escopo desta fase

Processos judiciais, gerenciamento completo de prazos, andamentos, documentos,
tarefas/agenda e frontend — nenhuma dessas frentes foi alterada.
