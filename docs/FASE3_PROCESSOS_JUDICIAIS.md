# Fase 3 — Gerenciamento de Processos Judiciais

Evolução do sistema de gestão de escritório: cadastrar, consultar, atualizar,
arquivar e auditar **processos judiciais** vinculados aos casos, preservando
integralmente as Fases 1 e 2.

## 1. Conceito central

**`Caso` ≠ `ProcessoJudicial`.** O caso é a **demanda jurídica** do cliente
(pode ser administrativa, extrajudicial ou judicial); o processo judicial é a
**ação formalmente protocolada no Poder Judiciário**. Relacionamento **1:N**:

- Um caso pode existir **sem** processo judicial.
- Um caso pode ter **vários** processos (ex.: 1ª e 2ª instância).
- Todo processo pertence a exatamente um caso (`caso_id` obrigatório).

O campo legado `Caso.numero_processo` **não foi removido nem alterado**: ele
continua aceito em `CasoCreate` (compatibilidade com a Fase 2, sem validação
CNJ) e é apenas depreciado — a fonte de verdade de processos agora é a
entidade própria.

## 2. Modelo de dados

### `processos_judiciais` (nova — migration `0005_processos_judiciais`)

| Coluna | Tipo | Observação |
|---|---|---|
| `caso_id` | FK → `casos`, index, **NOT NULL** | `ON DELETE CASCADE` — vinculo N:1 obrigatório |
| `numero_processo` | VARCHAR(20), **UNIQUE** | **Normalizado**: 20 dígitos, sem máscara (ex.: `00000013520268260100`) |
| `tribunal` | VARCHAR(120), index | Filtro de listagem |
| `orgao_julgador` | VARCHAR(160) | Vara / órgão julgador |
| `comarca` | VARCHAR(120), index | Filtro de listagem |
| `instancia` | VARCHAR(20), index | `PRIMEIRA_INSTANCIA` / `SEGUNDA_INSTANCIA` |
| `classe_processual` | VARCHAR(80), index | Ex.: `Acao de Cobranca` |
| `assunto` | VARCHAR(200) | Assunto principal |
| `data_distribuicao` | DATE, index | Nunca futura (validado no service) |
| `status` | VARCHAR(30), index, NOT NULL | `DISTRIBUIDO` (default), `EM_ANDAMENTO`, `SUSPENSO`, `AGUARDANDO_SENTENCA`, `SENTENCA_PROFERIDA`, `BAIXADO`, `EXTINTO` |
| `valor_causa` | NUMERIC(14,2) | **CHECK `valor_causa >= 0`** no banco |
| `segredo_justica` | BOOL, NOT NULL | Default `false` |
| `observacoes` | TEXT | Opcional |
| `arquivado` / `arquivado_por` / `arquivado_em` | BOOL/FK/DATETIME | **Arquivamento do PROCESSO** (distinto do caso) |
| `criado_por` | FK → `usuarios`, `SET NULL` | Operador da criação |
| `criado_em` / `atualizado_em` | DATETIME | `onupdate` automático |

Propriedades de leitura (não são colunas): `numero_formatado`
(`0000001-35.2026.8.26.0100`) e `criado_por_nome`.

Índices: `caso_id`, `tribunal`, `comarca`, `instancia`, `classe_processual`,
`status`, `data_distribuicao`, `arquivado`.

### `processo_historicos` (nova)

Auditoria própria dos processos — espelha o padrão de `caso_historicos` da
Fase 2 (tabela separada para não misturar entidades; nenhum registro existente
foi modificado). **Sem endpoint de escrita**:

- `processo_id` (FK → `processos_judiciais`, `ON DELETE CASCADE`, index),
  `usuario_id` (FK → `usuarios`, `SET NULL`)
- `operacao`: `CRIACAO` | `ATUALIZACAO` | `MUDANCA_STATUS` | `ARQUIVAMENTO`
- `dados` (JSON): apenas campos alterados
  (`{"status": {"antes": "...", "depois": "..."}}`)
- `criado_em`

### `usuario_casos` (evoluída)

Nova coluna `pode_gerenciar_processos` BOOL NOT NULL DEFAULT `0` — nenhuma
permissão existente cobre gestão de processos, e o menor privilégio exige
default `False`.

## 3. Estratégia do número CNJ

- **20 dígitos**: `NNNNNNN-DD.AAAA.J.TR.OOOO`.
- **Validação real dos dígitos verificadores** (não regex): o número completo
  interpretado como inteiro deve ter **resto 1 na divisão por 97**
  (`int(numero) % 97 == 1`, algoritmo módulo 97 do padrão CNJ).
  `core/validacao.py` expõe `eh_cnj`, `normalizar_numero_processo` (aceita com
  ou sem máscara → devolve os 20 dígitos; `NumeroProcessoInvalidoError` →
  `422`) e `formatar_numero_processo` (exibição).
- **Armazenamento normalizado** (20 dígitos sem máscara) — consistente com a
  política de CPF/CNPJ — e `UNIQUE` do banco sobre a forma normalizada.
- A entrada pode vir com máscara ou só dígitos; a saída traz `numero_processo`
  (normalizado) e `numero_formatado`.

### Backfill seletivo (dados legados)

A migration 0005 **migra `casos.numero_processo` → `processos_judiciais`
somente quando o número é CNJ-válido** (a maioria dos números legados/seed não
é — DD arbitrário):

- Válido → vira `ProcessoJudicial` (normalizado; `tribunal`/`vara` copiados;
  `status = EM_ANDAMENTO`) + registro `CRIACAO` com
  `dados = {"origem": "MIGRACAO_LEGADA"}`.
- Inválido/`NULL` → permanece apenas no caso legado (**coluna mantida,
  intacta**).
- A validação do módulo 97 foi feita em Python dentro da migration (não
  portável em SQL entre SQLite e MySQL).

## 4. Endpoints

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/api/casos/{caso_id}/processos` | Escrita no caso + CSRF | Cadastra processo CNJ no caso → `201` |
| GET | `/api/casos/{caso_id}/processos` | Escopo Fase 1 | Processos do caso (`?incluir_arquivados=true`) |
| GET | `/api/processos` | Escopo Fase 1 | Listagem geral paginada no banco + filtros |
| GET | `/api/processos/{id}` | Escopo Fase 1 | Detalhe (`404` fora do escopo; arquivado consultável) |
| PATCH | `/api/processos/{id}` | Escrita no caso + CSRF | Atualização parcial (`extra="forbid"`) → `200` |
| PATCH | `/api/processos/{id}/status` | Escrita no caso + CSRF | Mudança de situação (encerramento `BAIXADO`/`EXTINTO`) → `200` |
| POST | `/api/processos/{id}/arquivar` | Escrita no caso + CSRF | Soft delete do **processo** → `200`; repetido → `409` |
| GET | `/api/processos/{id}/historico` | Escopo Fase 1 | Auditoria (somente leitura) |

Não existe `POST /api/processos` (avulso): o cadastro é sempre pelo caso.
Não existe `DELETE` de processo: arquivamento é lógico.

### Filtros (`GET /api/processos`)

`q` (busca pelo **número CNJ**, aceita com máscara ou só dígitos — termo sem
dígitos não casa com todos), `caso_id`, `tribunal`, `comarca`, `instancia`,
`classe_processual`, `status`, `distribuicao_de`/`distribuicao_ate`,
`arquivados`, `pagina`/`limite` (máx 100). Tudo executado **no banco**
(count + offset/limit) sob `condicao_processo_visivel`.

## 5. Regras de negócio e autorização

### Escopo de leitura (Fase 1 herdada)

`escopo.py` ganhou `condicao_processo_visivel`: processo é visível quando o
**caso** é visível (admin vê tudo; demais só com concessão ativa +
`pode_visualizar`). **Um processo nunca dá acesso indireto a um caso não
autorizado → `404`** (mesmo código do inexistente), inclusive em detalhe,
histórico, filtros e busca.

### Escrita (criar / atualizar / status / arquivar)

Ordem das verificações:

1. **Caso existe e está no escopo** → senão `404`.
2. **Permissão de escrita**: admin **ou** responsável pelo caso **ou** linha
   ativa em `usuario_casos` com `pode_gerenciar_processos` → senão `403`.
   Funcionário só cadastra/edita processo quando o admin lhe concede esse
   grant (advogado com mero acesso de visualização também → `403`).
3. **Caso arquivado não recebe novos processos** → `422` (reabrir é papel do
   admin; o arquivamento do caso continua sendo distinto do do processo).

### Cadastro

- Número CNJ obrigatório e válido (dígitos verificadores) → `422`.
- Duplicidade (global, sobre a forma normalizada) → `409` (também em corrida,
  via `IntegrityError`).
- `caso_id`, `criado_por`, `cliente_id`, `arquivado*` **não são aceitos** no
  payload (`extra="forbid"` → `422`): o vínculo vem da URL, o criador é o
  operador autenticado. Não há como vincular cliente direto ao processo.
- `data_distribuicao` futura → `422`; `valor_causa` negativa → `422`
  (schema `ge=0` + CHECK no banco); `instancia`/`status` fora do enum → `422`.

### Atualização (`PATCH`)

- Mesma regra de escrita (admin/responsável/grant) e escopo (`404`).
- `caso_id`/`criado_por` no payload → `422` (não altera vínculo nem criador).
- Número alterado é **revalidado** (CNJ) e re-checado em duplicidade
  (reenviar o próprio número não conflita) → `422`/`409`.
- Payload sem mudanças reais → nada é gravado nem auditado.

### Status e encerramento

- `PATCH /{id}/status` aceita os 7 status (inválido → `422`); `BAIXADO` e
  `EXTINTO` representam encerramento; mesmo status não audita.
- Registro `MUDANCA_STATUS` com antes/depois.

### Arquivamento do processo

- Soft delete próprio (`arquivado/por/em`), **distinto do caso**: um processo
  pode ser arquivado enquanto o caso continua ativo (outras demandas).
- Repetido → `409`; fora das listagens padrão; consultável por id e por
  `?arquivados=true` / `?incluir_arquivados=true`.
- Caso arquivado preserva os processos (e vice-versa). Nunca há exclusão
  física.
- Escrita usa a mesma regra (admin/responsável/grant); `403`/`404` como nas
  demais operações.

## 6. Auditoria

Tabela própria `processo_historicos` (justificativa: `caso_historicos` tem
`caso_id NOT NULL` e misturaria entidades; nenhum registro existente foi
alterado). Operações registradas pelos services:

- `CRIACAO` (também no backfill, com origem `MIGRACAO_LEGADA`)
- `ATUALIZACAO` (campos alterados, antes/depois)
- `MUDANCA_STATUS`
- `ARQUIVAMENTO`

Somente leitura pela API (`GET /{id}/historico`), respeitando o escopo do
processo; sem dados sensíveis.

## 7. Migrations

`0005_processos_judiciais` (revises `0004_casos_gestao`):

- **Upgrade**: cria `processos_judiciais` (FKs, UNIQUE `uq_processos_numero`,
  CHECK `ck_processos_valor_causa`, 8 índices), cria `processo_historicos`
  (+ índice), adiciona `usuario_casos.pode_gerenciar_processos`
  (`server_default = 0`), **backfill seletivo** dos números CNJ-válidos com
  auditoria `CRIACAO`.
- **Downgrade**: remove índice/tabelas/coluna — a única perda são os dados
  criados na Fase 3 (processos migrados/criados e sua auditoria); `casos.
  numero_processo` permanece intacto.
- **Re-upgrade**: repetível (mesmo backfill determinístico).
- Migrations antigas intocadas; nenhum registro legado apagado.

**Validação executada**: upgrade → conferência (tabelas, colunas, backfill
seletivo = 1 válido migrado / inválido e NULL não migrados, UNIQUE/CHECK
efetivos, 8+1 índices, coluna de permissão, auditoria do backfill, legado
intocado) → downgrade da 0005 → downgrade até 0002 (marcadores `S/N-` da Fase
2) → re-upgrade — em banco SQLite descartável
(`tests/test_migracoes.py`). SQL offline do MySQL inspecionado
(`alembic upgrade head --sql`): `CREATE TABLE ... CHECK`, `CREATE INDEX` e
`ADD COLUMN pode_gerenciar_processos BOOL NOT NULL DEFAULT 0` corretos.

## 8. Testes

`tests/test_fase3.py` — **76 testes**, todos com HTTP real (mais testes
unitários do CNJ):

- **CNJ (unidade)**: resto módulo 97, gerador por varredura de DD, tamanho
  errado, dígitos iguais, normalização com/sem máscara, rejeição de DD
  incorreto, round-trip de formatação.
- **Cadastro**: válido `201` (normalizado + formatado + criador), sem máscara,
  status default, DD inválido (`422`), número curto (`422`), duplicado global
  e no mesmo caso (`409`), caso inexistente (`404`), caso arquivado (`422`),
  fora do escopo (`404`), funcionário sem grant (`403`) e com grant (`201`),
  responsável (`201`), advogado com grant (`201`), grant revogado (`404`),
  payload com `caso_id`/`criado_por`/`cliente_id`/`arquivado` (`422`), data
  futura (`422`), valor negativo (`422`), instância/status inválidos
  (`422`), sem sessão (`401`), sem CSRF (`403`).
- **Consulta/listagem**: detalhe (`200`), inexistente/alheio (`404`), por caso
  (com escopo → `404`), caso sem processos, paginação no banco (páginas
  disjuntas), todos os filtros (tribunal/comarca/instância/classe/status/
  período/`q` com máscara e parcial/`q` sem dígitos/`caso_id`), escopo não
  burlado por filtro/busca, arquivados fora do padrão e visíveis por flag,
  arquivado consultável por id.
- **Atualização**: admin/responsável/grant (`200`), sem grant (`403`), alheio
  (`404`), `caso_id`/`criado_por` no payload (`422` e vínculo intacto),
  número revalidado/normalizado, DD ruim (`422`), duplicado (`409`), mesmo
  número (`200`), sem mudança não audita.
- **Status**: mudança (`200`), encerramento `BAIXADO` com
  `MUDANCA_STATUS` antes/depois, inválido (`422`), igual não audita,
  funcionário sem grant (`403`).
- **Arquivamento**: `200` com rastreio, repetido (`409`), **processo vs caso
  (caso segue ativo com os demais processos)**, arquivar caso preserva
  processos, funcionário sem grant (`403`), alheio (`404`), sem CSRF (`403`).
- **Histórico**: CRIACAO/ATUALIZACAO/ARQUIVAMENTO, campos antes/depois,
  autor da operação, escopo (`404`), ausência de escrita, imutabilidade das
  entradas antigas.
- **Integridade/legado**: 1:N (vários processos por caso), caso sem
  processos, criação avulsa inexistente, relationships no banco, criação de
  processo **não altera** `Caso.numero_processo` (legado intacto e legível),
  `CasoCreate` legado sem CNJ **não gera** processo automático, propagação do
  grant `pode_gerenciar_processos` pela API.

`tests/test_migracoes.py` estendido: backfill seletivo (1 válido / inválido
não migrado / NULL não migrado), auditoria `MIGRACAO_LEGADA`, UNIQUE/CHECK
efetivos, índices, coluna de permissão, downgrade da 0005 (tabelas/coluna
removidas, casos preservados), downgrade ao 0002 e re-upgrade repetível.

**Suíte completa executada à época da Fase 3: 274 testes aprovados, 0 falhas**
(`test_unit` 41 + `test_api` 32 + `test_fase1` 47 + `test_fase2` 52 +
`test_validacao` 24 + `test_migracoes` 2 + `test_fase3` 76).
> **Atualização (04/11/2026, pré-entrega):** suíte completa com a Fase 4
> incluída — **376 testes aprovados, 0 falhas**.

## 9. Fora do escopo desta fase

Prazos completos (sem FK `processo_id` — sem consumidor nesta fase, fica para
a fase de prazos), andamentos completos, documentos/anexos, tarefas/agenda,
integração com tribunais/consultas externas e frontend. Nenhuma dessas
frentes foi alterada.
