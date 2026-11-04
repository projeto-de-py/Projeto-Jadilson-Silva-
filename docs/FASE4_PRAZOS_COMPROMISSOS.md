# Fase 4 — Prazos e Compromissos de Agenda

Evolução do sistema de gestão de escritório: completar os **prazos**
(entidade própria, com vencimento, status e auditoria) e criar os
**compromissos de agenda** (audiências, reuniões, atendimentos), preservando
integralmente as Fases 1 a 3.

## 1. Conceito central

**`Prazo` ≠ `Compromisso`.** São entidades distintas e nunca se misturam:

- **Prazo**: obrigação com **data de vencimento** (data pura, sem horário),
  sempre vinculada a um **caso** (e opcionalmente a um processo judicial do
  mesmo caso). É o objeto de "urgência": vence hoje, está vencido, vence em
  N dias.
- **Compromisso**: evento de agenda com **horário de início e fim**
  (`data_inicio`/`data_fim`), podendo inclusive **não ter caso** (agenda
  pessoal do escritório). Não tem noção de "vencido".

A agenda (`GET /api/agenda`) retorna **somente compromissos** — um prazo
jurídico nunca aparece nela.

Os dados legados de `prazos` foram **evoluídos na mesma tabela** (migration
`0006`, backfill reversível), sem criar estrutura paralela:

- `data_limite` → `data_vencimento` (coluna renomeada, mesmo valor);
- `cumprido` → `status` (`'CONCLUIDO'` quando cumprido, senão `'PENDENTE'`).

No ORM os nomes antigos continuam funcionando (`data_limite` como synonym de
`data_vencimento`; `cumprido` como propriedade derivada do `status`) para não
quebrar dados e testes legados.

## 2. Modelo de dados

### `prazos` (evoluída — migration `0006_prazos_compromissos`)

| Coluna | Tipo | Observação |
|---|---|---|
| `caso_id` | FK → `casos`, **NOT NULL** | `ON DELETE CASCADE` — todo prazo tem caso |
| `processo_id` | FK → `processos_judiciais`, anulável | **Opcional**; precisa ser do **mesmo caso**; `SET NULL` |
| `titulo` | VARCHAR(160), NOT NULL | Obrigatório (3–160) |
| `descricao` / `observacoes` | TEXT | Opcionais |
| `tipo` | VARCHAR(60), index | `PROCESSUAL`/`ADMINISTRATIVO`/`CONTRATUAL`/`INTERNO`/`OUTRO` |
| `data_inicio` | DATE, anulável | Início do período (quando houver) |
| `data_vencimento` | DATE, **NOT NULL**, index | Vencimento (era `data_limite`) |
| `status` | VARCHAR(20), index | `PENDENTE` (default), `EM_ANDAMENTO`, `CONCLUIDO`, `CANCELADO` |
| `prioridade` | VARCHAR(10), index | `BAIXA`/`MEDIA`/`ALTA`/`URGENTE` |
| `responsavel_id` | FK → `usuarios`, anulável | Usuário **ativo com acesso ao caso** |
| `criado_por` / `concluido_por` | FK → `usuarios`, anulável | Operador / quem concluiu |
| `criado_em` / `atualizado_em` | DATETIME (UTC) | `onupdate` automático |
| `concluido_em` | DATETIME, anulável | Preenchido **só** na conclusão |

**`vencido` NÃO existe como coluna**: é propriedade calculada (sempre em
aberto e `data_vencimento < hoje` local de Brasília). Legados: `data_limite`
(synonym) e `cumprido` (derivado de `status`).

Índices novos: `tipo`, `data_vencimento`, `status`, `prioridade`,
`responsavel_id`, `processo_id`.

### `compromissos` (nova)

| Coluna | Tipo | Observação |
|---|---|---|
| `caso_id` | FK → `casos`, **anulável** | Sem caso = agenda pessoal (**só o admin** enxerga) |
| `processo_id` | FK → `processos_judiciais`, anulável | Exige `caso_id` e o **mesmo caso** |
| `titulo` | VARCHAR(160), NOT NULL | Obrigatório (3–160) |
| `descricao` | TEXT | Opcional |
| `tipo` | VARCHAR(30), index | `AUDIENCIA`/`REUNIAO`/`ATENDIMENTO`/`DILIGENCIA`/`OUTRO` |
| `data_inicio` / `data_fim` | DATETIME, **NOT NULL** | **Horário local de Brasília (naive)** |
| `local` | VARCHAR(200) | Opcional (vara, sala, endereço) |
| `responsavel_id` | FK → `usuarios`, anulável | Usuário ativo (com acesso ao caso quando houver) |
| `status` | VARCHAR(20), index | `AGENDADO` (default), `REALIZADO`, `CANCELADO` |
| `criado_por` | FK → `usuarios`, anulável | Operador autenticado |
| `criado_em` / `atualizado_em` | DATETIME (UTC) | Auditoria em UTC; horários de negócio em Brasília |

**CHECK** `ck_compromissos_periodo`: `data_fim > data_inicio` (reforçado no
schema Pydantic e revalidado no service após o merge do `PATCH`).

Índices: `caso_id`, `processo_id`, `tipo`, `data_inicio`, `data_fim`,
`responsavel_id`, `status`.

### `prazo_historicos` e `compromisso_historicos` (novas)

Auditoria própria de cada entidade — mesmo padrão de `processo_historicos`
(Fase 3), tabela separada para não misturar entidades. **Sem endpoint de
escrita** (imutável pela API):

- FK do registro (`prazo_id` / `compromisso_id`, `ON DELETE CASCADE`, index),
  `usuario_id` (`SET NULL`)
- `operacao`: ver §6
- `dados` (JSON): apenas campos alterados
  (`{"status": {"antes": "...", "depois": "..."}}`)
- `criado_em`

### `usuario_casos` (evoluída — migration `0007`)

Nova coluna `pode_gerenciar_compromissos` BOOL NOT NULL DEFAULT `0`.
**Sem backfill de privilégio**: as linhas existentes nascem com `False`
(menor privilégio) e o admin concede caso a caso pela API. Ver §5.

## 3. Tempo local do escritório (`app/core/tempo.py`)

- `BRASILIA = timezone(timedelta(hours=-3))` — **fuso fixo UTC-3** (o Brasil
  não tem horário de verão desde 2019; `zoneinfo` exigiria o pacote
  `tzdata`, indisponível no ambiente).
- `agora_brasilia()` / `hoje_brasilia()`: data/hora **local naive** usada em
  todo cálculo de vencimento, classificação de urgentes e filtro da agenda.
- **Auditoria continua em UTC** (`utcnow()` em `models/usuario.py`): campos
  `criado_em`/`atualizado_em`/`concluido_em` são UTC; horários de negócio
  (`compromissos.data_inicio/data_fim`) são locais.
- Datetime com fuso enviado na API é **convertido para Brasília** no schema
  (`_local_brasilia`); naive é assumido como local.

## 4. Endpoints

### Prazos — `/api/prazos`

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/api/prazos/urgentes` | Escopo Fase 1 | Vencidos + hoje + próximos `dias` (máx. 90) |
| POST | `/api/prazos` | Escrita no caso + CSRF | Cadastra prazo → `201` (status nasce `PENDENTE`) |
| GET | `/api/prazos` | Escopo Fase 1 | Listagem paginada no banco + filtros |
| GET | `/api/prazos/{id}` | Escopo Fase 1 | Detalhe (`404` fora do escopo) |
| PATCH | `/api/prazos/{id}` | Escrita no caso + CSRF | Atualização parcial (`extra="forbid"`) → `200` |
| PATCH | `/api/prazos/{id}/concluir` | Escrita no caso + CSRF | Conclusão (registra data/hora/usuário) → `200` |
| PATCH | `/api/prazos/{id}/reabrir` | Escrita no caso + CSRF | Reabre concluído/cancelado **preservando o histórico** → `200` |
| PATCH | `/api/prazos/{id}/cancelar` | Escrita no caso + CSRF | Cancela prazo em aberto → `200` |
| GET | `/api/prazos/{id}/historico` | Escopo Fase 1 | Auditoria (somente leitura) |

`/urgentes` é declarada **antes** de `/{prazo_id}` para não ser lida como id.

**Filtros (`GET /api/prazos`)**: `q` (título/descrição), `caso_id`,
`processo_id`, `responsavel_id`, `tipo`, `status`, `prioridade`,
`vencimento_de`/`vencimento_ate`, `vencidos`, `pendentes`, `concluidos`,
`pagina`/`limite` (máx. 100). Tudo executado **no banco** (count +
offset/limit) sob `condicao_prazo_visivel`.

- `pendentes=true` = **em aberto** (`PENDENTE` + `EM_ANDAMENTO`);
  `pendentes=false` = fechado (`CONCLUIDO` + `CANCELADO`).
- `vencidos` usa `data_vencimento < hoje` **de Brasília** no banco.

**`GET /api/prazos/urgentes?dias=7`**: retorna `itens`, `total`, `pagina`,
`limite` e `dias`, com classificação **calculada** por item:

| `situacao` | Condição |
|---|---|
| `VENCIDO` | `data_vencimento < hoje` (Brasília) |
| `HOJE` | `data_vencimento == hoje` |
| `PROXIMO` | `hoje < data_vencimento <= hoje + dias` |

Restrições: somente **em aberto**, horizonte `dias` entre **0 e 90** (`422`
acima), ordenação por situação → prioridade → data, paginação no banco, e os
itens trazem também `numero_processo` e `cliente` do caso (sem exigir abrir
o detalhe). `vencido` acompanha a situação (`true` só em `VENCIDO`).

### Compromissos — `/api/compromissos`

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/api/compromissos` | Escrita no caso (ou admin, se sem caso) + CSRF | Cadastra → `201` (status nasce `AGENDADO`) |
| GET | `/api/compromissos` | Escopo Fase 1 | Listagem paginada no banco + filtros |
| GET | `/api/compromissos/{id}` | Escopo Fase 1 | Detalhe (`404` fora do escopo/sem caso p/ não-admin) |
| PATCH | `/api/compromissos/{id}` | Escrita no caso + CSRF | Atualização parcial (`extra="forbid"`) → `200` |
| PATCH | `/api/compromissos/{id}/status` | Escrita no caso + CSRF | **Único caminho do status** → `200` |
| GET | `/api/compromissos/{id}/historico` | Escopo Fase 1 | Auditoria (somente leitura) |

**Filtros (`GET /api/compromissos`)**: `q`, `caso_id`, `processo_id`,
`responsavel_id`, `tipo`, `status` (alias do query param), `inicio_de` /
`inicio_ate` (dia inteiro local), `pagina`/`limite`.

### Agenda — `/api/agenda`

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/api/agenda` | cookie (autenticação; **sem acesso público**) | Recorte temporal dos compromissos |

Query params: `de` (padrão: **hoje** Brasília), `ate` (padrão: `de` + 30
dias), `responsavel_id`, `pagina`, `limite` (máx. 100). Resposta acrescenta
`de`/`ate` ao formato de página.

- **Semântica de sobreposição**: entra tudo que **atravessa** o período —
  `data_fim >= início(do dia de)` **E** `data_inicio <= fim(do dia ate)`.
  Um evento que começa no dia anterior às 22h e termina às 6h do dia `de`
  **aparece**; um evento inteiro anterior ao período não aparece.
- `ate < de` → `422`; período maior que **366 dias** → `422`.
- Ordenado por `data_inicio`; **nunca mistura prazos**.

## 5. Regras de negócio e autorização

### Escopo de leitura (Fase 1 herdada)

`escopo.py` ganhou `condicao_compromisso_visivel`:

- compromissos **com caso** herdam a visibilidade do caso (admin vê tudo;
  demais só com concessão ativa + `pode_visualizar`);
- compromissos **sem caso** pertencem **somente ao administrador** (a agenda
  nunca fica pública).

Fora do escopo responde **`404`** (mesmo código do inexistente), inclusive em
detalhe, histórico, filtros e busca — um prazo/compromisso nunca revela caso
alheio.

### Escrita de prazos

Ordem das verificações:

1. **Caso existe e está no escopo** → senão `404`.
2. **Permissão de escrita**: admin **ou** responsável pelo caso **ou** linha
   ativa em `usuario_casos` com `pode_gerenciar_prazos` → senão `403`.
3. **Caso arquivado não recebe novos prazos** → `422`.
4. **Processo (opcional)** precisa existir, estar **no mesmo caso** e (para
   novo vínculo) não estar arquivado → `422`.
5. **Responsável**: usuário **ativo** e **com acesso ao caso** (admin,
   responsável do caso ou concessão ativa) → `422`. Sem `responsavel_id`, o
   responsável é o próprio operador — nunca fica sem responsável.

Sem escalada pelo payload: o status **nasce `PENDENTE`** e `concluido_*` só
é preenchido na conclusão, pela rota própria.

### Escrita de compromissos

1. **Compromisso com caso**: mesma estrutura (escopo → `404`; permissão →
   `403`), mas com a permissão **própria** `pode_gerenciar_compromissos`:
   admin, responsável pelo caso ou o grant de compromissos.
   **`pode_gerenciar_prazos` NÃO autoriza compromissos** (recuso implícito:
   agenda é recurso distinto).
2. **Compromisso sem caso**: **somente o administrador** cria/edita —
   qualquer outro usuário → `403` (ou `404` na leitura).
3. **`data_fim > data_inicio`** (schema + service) → `422`.
4. **`processo_id` exige `caso_id`** e o processo precisa pertencer ao
   mesmo caso → `422`.
5. Caso arquivado → `422`; responsável inativo/sem acesso → `422`.

**Status só via `PATCH /{id}/status`** (`AGENDADO`/`REALIZADO`/`CANCELADO`):
`status` não é aceito em `POST` nem em `PATCH` comum (`extra="forbid"` →
`422`), assim como `caso_id`/`criado_por`/`id` — o caso nasce na URL e não
muda, o criador é o operador autenticado. Mesmo status não gera auditoria.

### Concessão da permissão (API)

`POST /api/casos/{id}/usuarios` (admin) aceita
`pode_gerenciar_compromissos` (junto com os demais grants); linha ativa
repetida → `409`; `DELETE /{id}/usuarios/{usuario_id}` revoga (soft:
`ativo=False` + rastreio) e **re-conceder reativa a mesma linha já com os
campos novos** (UNIQUE `usuario_id+caso_id`).

## 6. Auditoria

Tabela própria por entidade (justificativa: separar entidades e preservar o
padrão das fases anteriores). Operações registradas pelos services:

| `PrazoHistorico` | `CompromissoHistorico` |
|---|---|
| `CRIACAO` | `CRIACAO` |
| `ATUALIZACAO` (campos alterados, antes/depois) | `ATUALIZACAO` (idem) |
| `MUDANCA_VENCIMENTO` (entrada própria) | `MUDANCA_RESPONSAVEL` (entrada própria) |
| `MUDANCA_RESPONSAVEL` (entrada própria) | `CANCELAMENTO` (mudança de status para `CANCELADO`) |
| `CONCLUSAO` / `REABERTURA` / `CANCELAMENTO` | — |

- Payloads idênticos **não gravam** registro (nada mudou = nada a auditar).
- `GET /{id}/historico` respeita o escopo e **não existe escrita**.
- Reabertura **preserva** o histórico integral (`REABERTURA` entra como
  entrada nova; `CONCLUSAO`/`CRIACAO` permanecem intactos) e limpa
  `concluido_em`/`concluido_por`.

### ATOMICIDADE (garantia central da fase)

O repositório de negócio **não commita** (`flush()` apenas) e o repositório
de histórico também: o negócio e a auditoria compartilham **UMA transação**,
fechada pelo service (`PrazoService._transacao()` /
`CompromissoService._transacao()`):

- sucesso → `commit()` único (os dois persistem juntos);
- **qualquer falha** (inclusive no `INSERT` do histórico) → `rollback()`
  desfando **os dois** — não existe prazo/compromisso alterado sem a sua
  trilha de auditoria.

## 7. Migrations

### `0006_prazos_compromissos` (revises `0005_processos_judiciais`)

- **Upgrade**: evolui `prazos` (12 colunas novas + 4 FKs nomeadas), faz o
  **backfill reversível** (`data_limite`→`data_vencimento`,
  `cumprido`→`status`, responsável herdado do caso, `atualizado_em`), remove
  as colunas legadas e seus índices, cria 6 índices novos, cria
  `prazo_historicos` (+ índice) com **backfill de auditoria** dos prazos
  legados (`CRIACAO` com `origem: MIGRACAO_LEGADA`), cria `compromissos`
  (CHECK `data_fim > data_inicio`, 7 índices) e `compromisso_historicos`.
- **Downgrade**: remove só as tabelas/colunas novas e **reconstrói**
  `data_limite`/`cumprido` a partir de `data_vencimento`/`status` — os dados
  legados de `prazos` são preservados nos dois sentidos.
- Compatibilidade: `batch_alter_table` (ALTER TABLE puro no MySQL 8,
  recriação no SQLite), FKs nomeadas, CHECK aplicado por bancos com suporte.
- **Executado validado** em `tests/test_migracoes.py` (upgrade → conferência
  → downgrade → re-upgrade), em SQLite descartável.

### `0007_permissoes_compromissos` (revises `0006_prazos_compromissos`)

- **Upgrade**: `ADD COLUMN usuario_casos.pode_gerenciar_compromissos BOOLEAN
  NOT NULL DEFAULT 0` — **incremental**, sem backfill de privilégio (ninguém
  recebe a permissão automaticamente).
- **Downgrade**: remove somente a coluna nova.
- Testes de migration cobrem: coluna presente, **0 linhas concedidas**
  automaticamente, estado da linha pré-0007 intacto e downgrade removendo a
  coluna.

> **Banco MySQL real:** em 04/11/2026 (pré-entrega) as migrations 0003–0007
> foram **aplicadas** lá com autorização, backup prévio e conferência de schema
> — hoje está em `0007_permissoes_compromissos` (detalhes no `README.md` da
> raiz). Na época da conclusão desta fase o banco estava em `0002_casos_prazos`.

## 8. Testes

`tests/test_fase4.py` — **102 testes**, todos com HTTP real (status + corpo):

- **Cadastro de prazos**: `201` (status `PENDENTE`, `vencido=false`,
  responsável = operador), período invertido (`422`), caso inexistente
  (`404`), caso arquivado (`422`), fora do escopo (`404`), sem grant (`403`)
  e com grant `pode_gerenciar_prazos` (`201`), responsável do caso (`201`),
  responsável inativo/sem acesso (`422`), payload com
  `status`/`criado_*`/`concluido_*`/`id`/`vencido` (`422`), sem sessão
  (`401`), sem CSRF (`403`).
- **Consulta/filtros/paginação**: detalhe (`200`) e alheio (`404`),
  `tipo`/`prioridade`/`q`/`caso_id`/`vencimento_de`/`vencimento_ate`,
  **`pendentes` = em aberto** (PENDENTE + EM_ANDAMENTO; concluído sai),
  páginas disjuntas no banco, escopo não burlado por filtro (`caso_id`
  alheio → `total = 0`).
- **Urgentes**: classificação `VENCIDO`/`HOJE`/`PROXIMO` na data de Brasília,
  ordenação por situação, campos extras `numero_processo`/`cliente`,
  `dias=91` → `422` e `dias=90` → `200`, só em aberto (concluído e
  **cancelado** fora), escopo, paginação no banco.
- **Edição de prazos**: PATCH parcial (`200`), campos proibidos incluindo
  `status=CONCLUIDO` (`422`), período pós-merge (`422`), concluído não edita
  (`409`), alheio (`404`).
- **Transições de prazo**: concluir registra `concluido_em/por` e zera
  `vencido`, duplo concluir (`409`), cancelar (`200`), concluir cancelado
  (`409`), reabrir limpa a conclusão e **preserva o histórico**
  (`REABERTURA` → `CONCLUSAO` → `CRIACAO`), reabrir aberto (`409`),
  transições fora do escopo (`404`).
- **Histórico de prazos**: `CRIACAO` com autor, `ATUALIZACAO` antes/depois,
  `MUDANCA_VENCIMENTO`/`MUDANCA_RESPONSAVEL` como entradas próprias,
  `CONCLUSAO`/`REABERTURA`/`CANCELAMENTO`, atualização idêntica não grava,
  escopo (`404`) e ausência de rota de escrita (`404`/`405`).
- **Atomicidade de prazos (3)**: falha simulada no `registrar` do histórico
  (monkeypatch) desfaz **criação**, **edição** e **conclusão** (sessão
  expirada + consulta no banco provando que nada persistiu).
- **Compromissos — cadastro**: `201` com caso, sem caso = **só admin**
  (`201`; advogado/funcionário `403`), `data_fim <= data_inicio` (`422`),
  processo de outro caso (`422`) e do mesmo caso (`201`), payload com
  `status`/`criado_por` (`422`) e PATCH com `caso_id`/`processo_id`/
  `status`/`criado_por`/`id` (`422`), caso arquivado (`422`), responsável
  inativo (`422`), `401`/`403`.
- **Permissões de compromissos**: grant `pode_gerenciar_compromissos` →
  `201`; **grant `pode_gerenciar_prazos` → `403`**; só `pode_visualizar` →
  `403`; sem acesso → `404`; revogação → `404`; concessão pela API
  (404 → 403 → revogação → reativação com o campo → `201`); responsável do
  caso cadastra sem grant (`201`).
- **Consulta de compromissos**: detalhe (`200`/`404`), **sem caso invisível
  para não-admin** (detalhe `404` e ausente da listagem), todos os filtros
  (`q`/`caso_id`/`processo_id`/`tipo`/`status`/`responsavel_id`/
  `inicio_de`/`inicio_ate`), paginação no banco, escopo não burlado, `401`.
- **PATCH de compromissos**: mescla válida (`200`), período invertido após
  o merge (`422` e nada alterado), campos proibidos (`422` com vínculo e
  status intactos), responsável sem acesso (`422`), sem grant (`403`),
  fora do escopo (`404`).
- **Rota `/status`**: `AGENDADO`→`REALIZADO` audita `ATUALIZACAO` com
  antes/depois e autor; cancelar audita **`CANCELAMENTO`**; status igual não
  grava; status inválido/falta/extra (`422`); sem grant (`403`); alheio
  (`404`).
- **Agenda**: período padrão (hoje → +30 dias), **sobreposição de evento
  que atravessa dias** (entra) vs. evento anterior (fora) e ordenação por
  início, `ate < de` (`422`), 367 dias (`422`) vs. 366 dias (`200`),
  **não mistura prazos**, filtro por responsável, escopo (só casos
  autorizados; sem caso só admin), `401`.
- **Histórico de compromissos**: `CRIACAO` com autor, antes/depois,
  `MUDANCA_RESPONSAVEL` próprio, atualização idêntica não grava, escopo
  (`404`) e imutabilidade (`404`/`405`).
- **Atomicidade de compromissos (3)**: falha na auditoria desfaz
  **criação**, **mudança de status** e **edição**.
- **Tempo (`core/tempo.py`)**: fuso fixo `UTC-3`, `agora_brasilia()` naive
  deslocada de `utcnow()` em exatamente −3h, `hoje_brasilia()` = data local
  (UTC no máximo 1 dia à frente), e datetime com fuso convertido para
  Brasília na API (`12:00Z` → `09:00`).

`tests/test_migracoes.py` ampliado (**2 testes**): 0006 (backfill reversível
de `prazos`, tabelas/índices/CHECK, auditoria `MIGRACAO_LEGADA`, downgrade
reconstruindo o legado) e **0007** (coluna presente, sem auto-grant,
downgrade removendo a coluna).

**Suíte completa executada: 376 testes aprovados, 0 falhas**
(`test_unit` + `test_api` + `test_fase1` + `test_fase2` + `test_validacao` +
`test_migracoes` + `test_fase3` + `test_fase4` 102) — baseline da Fase 4 era
**274 testes, 0 falhas**; nenhuma regressão nas Fases 1–3.

## 9. Fora do escopo desta fase

Andamentos completos (RF06 — tabela existe, sem endpoint), documentos/anexos,
tarefas, notificações, cálculo automático de prazo processual (a data é
informada manualmente pelo profissional), frontend e MinutaIA. Nenhuma dessas
frentes foi alterada.
