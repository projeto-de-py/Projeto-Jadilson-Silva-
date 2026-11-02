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
| POST | `/api/usuarios` | **Admin** + CSRF | Cadastra usuário (`ADVOGADO` ou `FUNCIONARIO`) |
| PATCH | `/api/usuarios/{id}` | **Admin** + CSRF | Ativa/desativa ou troca o perfil (nunca aceita `administrador`) |
| GET | `/api/casos` | cookie | Lista casos **do escopo do usuário** (Admin vê todos) com filtros (`q`, `cliente_id`, `area`, `status`, `prioridade`, `responsavel_id`, `tipo_demanda`) e ordenação (`ordenar=abertura|prioridade`) |
| GET | `/api/casos/arquivados` | cookie | Lista casos **arquivados** do escopo (declarada antes de `/{id}`) |
| POST | `/api/casos` | **Advogado** + CSRF | Cria caso (judicial/extrajudicial/administrativo — `numero_processo` opcional) |
| GET | `/api/casos/{id}` | cookie | Detalhe do caso (`404` se fora do escopo; arquivados continuam consultáveis) |
| PATCH | `/api/casos/{id}` | **Admin ou responsável** + CSRF | Atualiza dados gerais (`extra="forbid"`: sem campos administrativos) |
| POST | `/api/casos/{id}/arquivar` | **Admin** + CSRF | Arquivamento lógico (soft delete, rastreável; repetido → `409`) |
| GET | `/api/casos/{id}/historico` | cookie | Auditoria do caso (CRIACAO/ATUALIZACAO/ARQUIVAMENTO; somente leitura) |
| GET | `/api/casos/{id}/usuarios` | **Admin** | Usuários com acesso ao caso (`?incluir_revogados=true` mostra o histórico) |
| POST | `/api/casos/{id}/usuarios` | **Admin** + CSRF | Concede acesso de um usuário ao caso |
| DELETE | `/api/casos/{id}/usuarios/{usuario_id}` | **Admin** + CSRF | Revoga o acesso (soft delete, com rastreabilidade) |
| GET | `/api/clientes` | cookie | Lista clientes (Admin: todos; comum: só os dos casos autorizados) |
| POST | `/api/clientes` | **Admin** + CSRF | Cadastra cliente (PF/PJ, CPF/CNPJ validado) |
| GET | `/api/clientes/{id}` | cookie | Detalhe do cliente (`404` se fora do escopo) |

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

### Credenciais do seed (advogado principal)

O `python -m app.seed` **nao usa senha fixa no codigo**: se voce nao definir
`ADMIN_SENHA_INICIAL` no `.env`, ele gera uma senha aleatoria forte e imprime
uma unica vez no terminal (anote-a). Troque a senha apos o primeiro login.

A conta administrativa (`ADMIN_EMAIL`, padrao `admin@jadilson.adv`) e o **unico
ponto de provisionamento** da permissao `administrador` — nenhum cadastro ou
login permite que alguem escolha ser administrador.

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
- Permissões **sempre no servidor**: `require_admin` protege rotas Admin (RF02/RF07/RF08) e a autorização por caso é decidida em `app/repositories/escopo.py` — esconder botão no frontend não conta como controle de acesso
- **Escalada de privilégio impedida**: `administrador` não é aceito em nenhum payload (`extra="forbid"`) e `UsuarioUpdate` só aceita `ativo`/`perfil`; a permissao nasce apenas no provisionamento (`ADMIN_EMAIL`/seed)
- **404 em vez de 403** para casos/clientes fora do escopo: um usuário não descobre a existência de registros de outros advogados trocando o id da URL
- CORS liberado apenas para as origens configuradas (`CORS_ORIGINS`) com `allow_credentials`; as respostas de erro do CSRF também recebem os headers CORS
- **Fail-fast em produção** (`APP_ENV=production`): a API aborta o startup se o `JWT_SECRET` for fraco/default, se o cookie não for `Secure` ou se houver curinga no CORS; `/docs` e `/openapi.json` ficam desativados

## Testes

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest          # 198 testes (unit + API + Fase 1 + Fase 2 + migrations) — rodam em SQLite em memoria
```

- `tests/test_unit.py`: bcrypt, JWT (assinatura falsa/expirada), `Limiter`, services
- `tests/test_api.py`: login, cookie HttpOnly, CSRF, rate limit, `/me`, logout, autorização Admin
- `tests/test_fase1.py`: usuários, clientes (CPF/CNPJ) e permissões por caso (status HTTP reais)
- `tests/test_fase2.py`: casos — criação, filtros/paginação, atualização, arquivamento e histórico (52 testes)
- `tests/test_validacao.py`: CPF/CNPJ/telefone (unidade)
- `tests/test_migracoes.py`: upgrade/downgrade das migrations 0003 e 0004 em subprocesso (banco descartável)
- As fixtures (`tests/conftest.py`) sobrepõem `get_db` com SQLite em memoria — **nenhum teste toca no MySQL**

## Banco de dados

Tabelas: `usuarios` (`id, nome, email unique, senha_hash, perfil ADVOGADO|FUNCIONARIO, administrador, ativo, criado_em, atualizado_em`), `clientes` (`id, nome, cpf_cnpj unique (anulavel), email, telefone, data_nascimento, ativo, ...`), `usuario_casos` (`usuario_id + caso_id unique, pode_visualizar, pode_registrar_andamento, pode_gerenciar_prazos, ativo, concedido_por/em, revogado_por/em`), `casos` (Fase 2: `titulo, numero_processo anulavel unique, cliente_id FK, area, tipo_demanda, status, prioridade, data_abertura, responsavel_id FK, observacoes, arquivado/por/em, criado_por FK, atualizado_em, ...`), `caso_historicos` (auditoria imutavel: `caso_id FK, usuario_id FK, operacao, dados JSON, criado_em`), `andamentos` e `prazos`.

- **Produção/desenvolvimento:** MySQL (InnoDB, utf8mb4) via `DATABASE_URL` no `.env`
- **Teste local sem MySQL:** `$env:DATABASE_URL="sqlite:///./dev.db"`
- Migrações com **Alembic** (`alembic/versions/`) — nunca alterar tabela na mão

## Fase 1 - Cadastros e controle de acesso

A migration `0003_fase1_cadastros` (ver `docs/FASE1_CADASTROS.md`) evolui o `usuarios`
e cria `clientes` e `usuario_casos`:

- **Advogado principal** = conta `ADVOGADO` com a permissao `administrador` (provisionada
  pelo `ADMIN_EMAIL`/seed, nunca escolhida em cadastro ou login).
- **Visibilidade por caso**: colaborador e funcionário veem apenas os casos com concessao
  ativa em `usuario_casos` — e os clientes/prazos desses casos.
- **Revogação com rastreabilidade**: `DELETE /api/casos/{id}/usuarios/{usuario_id}` faz soft
  delete (`ativo=False` + `revogado_por/em`); re-conceder reativa a mesma linha (UNIQUE).
- **CPF/CNPJ validado** (dígitos verificadores, PF e PJ) com unicidade apenas para
  documentos presentes (ausente = NULL, permitido).

## Fase 2 - Gerenciamento de casos juridicos

A migration `0004_casos_gestao` (ver `docs/FASE2_GERENCIAMENTO_CASOS.md`) evolui `casos`
e cria a auditoria `caso_historicos`:

- **Caso nao e processo judicial**: `numero_processo` e opcional (demandas
  administrativas/extrajudiciais nao tem numero); o UNIQUE permanece e ignora NULL.
- **Criacao/editacao sao de advogado**: `POST /api/casos` e `PATCH /api/casos/{id}`
  exigem perfil `ADVOGADO` (funcionario → 403); a edicao e de **admin ou do responsavel**
  pelo caso.
- **Cliente acessivel**: a criacao/troca de cliente valida o escopo da Fase 1
  (admin: qualquer cliente ativo; comum: cliente dos casos autorizados → 404 fora do escopo).
- **Responsavel validado**: usuario ativo com perfil `ADVOGADO`; comum so pode assumir a
  propria responsabilidade (atribuir terceiros e do admin); criacao/troca garantem o
  acesso do responsavel e do criador (`concedido_por` = operador).
- **Arquivamento logico** (admin): `arquivado/por/em`, fora das listagens padrao,
  consultavel por `/arquivados` e por detalhe; sem exclusao fisica (prazos, andamentos e
  acessos preservados); repetido → 409.
- **Auditoria imutavel**: `GET /api/casos/{id}/historico` (CRIACAO/ATUALIZACAO/ARQUIVAMENTO
  com antes/depois por campo); nao ha endpoint de escrita.

## Próximos passos (fases)

1. ~~Tabelas `caso`, `caso_usuario`, `andamento`, `prazo` + escopo de visibilidade~~ ✅ Fase 1
2. ~~Edição de casos, vínculo cliente↔caso e arquivamento~~ ✅ Fase 2
3. Andamentos e documentos por caso (respeitando o mesmo escopo)
4. Prazos completos e agenda (RF10/RF11)
5. Tarefas
6. Módulo MinutaIA (Port/Adapter com mock)

## Casos e prazos

A migração Alembic `0002_casos_prazos` cria as tabelas `casos`, `andamentos` e `prazos` sem alterar as tabelas existentes. Após `alembic upgrade head`, execute `python -m app.seed` para carregar seis processos e quatro prazos fictícios; o seed pode ser repetido sem duplicar os registros demonstrativos.

- `GET /api/casos?q=&status=&area=&prioridade=&tipo_demanda=&responsavel_id=&cliente_id=&ordenar=&pagina=1&limite=20`: busca por título, número do processo, cliente ou parte contrária, com filtros, ordenação (abertura/prioridade) e paginação no banco.
- `GET /api/prazos/urgentes?dias=7&pagina=1&limite=20`: prazos em aberto vencidos ou com vencimento no intervalo informado.

As duas rotas exigem sessão autenticada. O limite máximo da página é 100 itens.

## IA do escritorio (`app/ia`)

Pasta de controle da IA. O comportamento e definido por arquivos de texto versionados:

| Pasta/arquivo | Para que serve |
|---|---|
| `perfis/` | Quem a IA "e": `redator_juridico.md` (sempre) + perfil da area (`trabalhista.md`, `bancario.md`, `previdenciario.md`) |
| `tarefas/` | Instrucao de cada acao (`resumo`, `contestacao`, `revisar`, `continuar`, `completar`) e o formato JSON obrigatorio da resposta |
| `guardrails/` | Entrada: odio/ameaca, injecao de prompt, mascara de CPF/CNPJ/e-mail/telefone. Saida: HTML saneado, citacoes marcadas `[CONFIRA A FONTE]` |
| `revisor.py` | Revisao objetiva (digitacao, gramatica, estilo, tom, requisitos da peca) - roda sem modelo |
| `provedores.py` | Unica porta para o modelo. Hoje `ProvedorSimulado` (offline). Provedor real: implementar `gerar()` aqui |
| `servico.py` | Fluxo: entrada -> contexto -> pergunta -> provedor -> validacao -> revisao -> saida -> auditoria |

Para ajustar o comportamento da IA, edite os `.md` (nenhum codigo). Cada resposta devolve `versao_prompt`
(hash do conjunto usado) e e auditada em `uso_ia` (so metadados, nunca o texto).

| Metodo | Rota | Acesso | Descricao |
|---|---|---|---|
| POST | `/api/ia/sugerir` | login + CSRF | `tarefa`: `resumo`/`contestacao`/`revisar`/`continuar`. Devolve `sugestoes`, `perguntas`, `avisos`. `caso_id` obedece o escopo dos casos (404 fora dele). Limite por usuario/hora |
| POST | `/api/ia/completar` | login + CSRF | Continuacao curta do texto (autocompletar). Limite por usuario/minuto |
| GET | `/api/ia/controle` | **Admin** | Inventario dos arquivos de controle (nome, tamanho, versao) - nao expoe o texto dos prompts |

Config (`.env`): `IA_PROVEDOR=simulado`, `IA_LIMITE_SUGERIR_HORA=60`, `IA_LIMITE_COMPLETAR_MINUTO=40`.


## Integracoes: assinatura (ZapSign), cobranca (Asaas) e IA real

| Metodo | Rota | Acesso | Descricao |
|---|---|---|---|
| POST | `/api/assinaturas` | **Admin** + CSRF | Envia um PDF (`pdf_base64`) ao ZapSign para o cliente assinar (WhatsApp/e-mail do cadastro). Valida que e PDF e no maximo 10 MB |
| GET | `/api/assinaturas` e `/{id}` | **Admin** | Lista/consulta o status (`ENVIADO`, `ASSINADO`, `RECUSADO`) |
| POST | `/api/financeiro/cobrancas` | **Admin** + CSRF | Emite cobranca Pix ou boleto, avulsa ou parcelada (ate 24x). Cria o cliente no Asaas na primeira vez |
| GET | `/api/financeiro/cobrancas` | **Admin** | Lista (`cliente_id`, `status`) |
| GET | `/api/financeiro/clientes/{id}/resumo` | **Admin** | Pendente, recebido e vencido do cliente |
| POST | `/api/v1/webhooks/zapsign` | segredo no header | Atualiza a assinatura para `ASSINADO` |
| POST | `/api/v1/webhooks/asaas` | token `asaas-access-token` | `PAYMENT_RECEIVED`/`CONFIRMED` -> RECEBIDA, `PAYMENT_OVERDUE` -> VENCIDA |

Seguranca dos webhooks: sem sessao nem CSRF (quem chama e o provedor), mas **fecham (503) se o segredo nao estiver
configurado**, comparam o segredo em tempo constante, aceitam no maximo 1 MB, **nao repetem a acao** para o mesmo evento
(`eventos_webhook`) e **confirmam o estado na API do provedor** antes de gravar (`WEBHOOKS_VERIFICAR_NA_API`).
Um pagamento recebido nunca volta para vencido por um evento atrasado.

Operacao: chaves so no `.env` (tipo `SecretStr`, nunca em log nem resposta); o Asaas usa o **sandbox por padrao**;
a IA real (`IA_PROVEDOR=openrouter`, modelo Google gratuito, chave em `OPENROUTER_API_KEY`) recebe so texto com CPF/CNPJ/e-mail/telefone mascarados e leva os exemplos few-shot
da materia (`app/ia/exemplos/`). Migration `0006`. Conferir nomes de campos e eventos na documentacao oficial de cada
servico antes de ligar em producao.

## Consultas publicas (feriados, CEP, CNPJ, juros do Banco Central, DataJud)

Arquitetura completa (camadas, classes e como adicionar uma API): [`docs/ARQUITETURA_INTEGRACOES.md`](../docs/ARQUITETURA_INTEGRACOES.md).

| Metodo | Rota | Acesso | Descricao |
|---|---|---|---|
| GET | `/api/consultas/feriados/{ano}?anos=3` | login | Feriados nacionais (BrasilAPI), usados na calculadora de prazos |
| GET | `/api/consultas/cep/{cep}` e `/cnpj/{cnpj}` | login | Endereco e dados publicos do CNPJ (BrasilAPI) |
| GET | `/api/consultas/juros/series` | login | Modalidades de juros disponiveis (Banco Central) |
| POST | `/api/consultas/juros/comparar` | login + CSRF | Compara a taxa do contrato com a media do BC no mes da contratacao |
| GET | `/api/consultas/processos/{numero}` | login | Andamentos no DataJud/CNJ (exige `DATAJUD_API_KEY`) |

Cada usuario tem um teto de consultas por minuto (`CONSULTAS_LIMITE_MINUTO`).

