# Operação da integração MySQL

Escopo: MySQL Connector/Python, banco existente `sistema`, tabelas `usuarios` e
`sessoes`. Não executar os preparadores antigos para aplicar estas revisões.
Nenhum comando deste documento foi executado para backup, restauração ou DDL.

## Conexões e transações

`database.py` mantém as interfaces `connect`, `one`, `execute`, `find_user`,
`session`, `create_session` e `revoke`. `create_session` aceita adicionalmente
`previous_digest` nomeado. O login passa o hash do cookie anterior, sem alterar
rotas, resposta, cookies, Argon2id ou regras de autenticação.

Cada operação abre conexão própria, usa UTC e utf8mb4 e encerra seu cursor antes
do commit. As leituras usam transação READ ONLY e cursor buffered. O resultado
buffered é apropriado para consultas pontuais/contagens; não usar `one` para
varreduras grandes. Não há pool compartilhado nem reconexão no meio de transação.

Revogação anterior e inserção da nova sessão agora usam uma conexão e um commit.
Falha no INSERT provoca rollback das duas operações. UPDATE pela PK usa os locks
do InnoDB. Duas requisições concorrentes de login podem criar sessões novas
independentes; não há política de sessão única por usuário. Logout é idempotente
na persistência. Não há exclusão/cascata de usuário ou sessão no código HTTP.

Falhas de rollback/close são registradas sem exceção, SQL ou parâmetros e não
ocultam a causa original. Close que falha após commit confirmado não transforma
a escrita confirmada em erro aparente. Em perda da confirmação de COMMIT, o
resultado pode ser indeterminado: não repetir INSERT/UPDATE automaticamente.
Uma chamada posterior abre conexão nova; não garante replay da chamada anterior.
Deadlocks/timeouts provocam falha/rollback, sem retry automático.

Timeouts validados de 1 a 120 segundos: `MYSQL_CONNECT_TIMEOUT` (5),
`MYSQL_READ_TIMEOUT` (10), `MYSQL_WRITE_TIMEOUT` (10). Os dois últimos exigem
Connector/Python >=9.2; o lock instalado já usa versão compatível. Nenhuma
instalação é necessária nesta entrega. Consultar `conexao.env.example` para
opções sem credenciais; nunca substituir o `.env` existente.

## TLS e credenciais

A conexão local auditada negociou TLS 1.3. Isso não comprova identidade do
servidor. Sem `MYSQL_SSL_CA`, o comportamento local de negociação do Connector é
preservado e pode aceitar servidor sem TLS. Com CA definida, certificado e
identidade são exigidos; usar nome DNS/IP que conste no certificado. Produção com
host remoto sem CA é rejeitada. A validação real com CA ainda precisa de teste
em ambiente isolado com certificado válido e casos negativos.

Manter `.env` fora do Git, com 0600, diretórios privados e acesso somente ao
operador/processo correspondente. Não passar senha em linha de comando. Backups,
binlogs e arquivos de configuração podem conter dados sensíveis. Revisar também
a proteção de `backend/.local/mysql/`, sem publicar seu conteúdo.

## Separação de contas — proposta não aplicada

| Papel | Privilégios propostos | Limites |
|---|---|---|
| HTTP | SELECT usuarios; SELECT das colunas consultadas, INSERT das colunas de criação e UPDATE somente revogada_em em sessoes | Sem alteração/cadastro de usuários, DELETE ou DDL |
| Cadastro | INSERT nome,email,senha_hash,perfil em usuarios | Sem leitura de hashes, UPDATE, sessoes ou DDL |
| Retenção | SELECT id_hash,expira_em e DELETE em sessoes | Credencial fora do processo HTTP; execução manual autorizada |
| Backup | SELECT e privilégios estritamente necessários às opções aprovadas do dump | Sem credencial no processo HTTP; revisar views/triggers se surgirem |

`revisoes/004_privilegios_proposta.sql` contém apenas comentários. Grants são
aditivos: conceder grants menores não remove os amplos existentes. Antes de
qualquer redução, provisionar a conta administrativa por canal seguro, adaptar
a configuração do comando `criar_usuario.py` para sua credencial independente e
testar em instância descartável. Hoje `Config.load()` exige `sistema_app` e o
cadastro continua funcionando com a configuração existente. Não revogar acesso
antes dessa transição. Não foram criadas contas ou alterados grants/credenciais.
A reversão deve usar inventário real de grants da janela, não suposições.

## Índices, integridade e revisão de esquema

Busca por e-mail utiliza UNIQUE `uq_usuarios_email`; sessão usa igualdade na PK
`id_hash`, JOIN pela PK do usuário e filtros de estado. Índices de usuário e
expiração já existem. Não foram adicionados índices: não há evidência para isso.
Não envolver e-mail indexado em LOWER na consulta; normalização segue no backend.

`revisoes/001_pre_validacao.sql` contém somente contagens/metadados.
`002_checks.up.sql` propõe `ativo IN (0,1)`, `expira_em > criado_em` e
`revogada_em IS NULL OR revogada_em >= criado_em`. O script down remove apenas
esses CHECKs. ENUM com modo SQL estrito e FK RESTRICT já protegem perfis/vínculos.
Não alterar charset/collation: mudar equivalência de e-mails exigiria auditoria.

Antes do DDL: autorização, backup restaurável, contagens sem violações, inspeção
dos nomes e ambiente isolado. MySQL valida dados existentes ao adicionar CHECK.
ALTER pode bloquear metadados/consumir recursos e causa commit implícito: não
prometer rollback transacional do conjunto. Registrar etapas aplicadas; em falha
parcial, reverter apenas CHECKs que realmente existem. Não usar `--force`, não
apagar dados para fazer uma restrição passar e não automatizar aplicação.

## Retenção — somente planejamento por padrão

`python -B banco/retencao_sessoes.py --dias 30` usa exclusivamente SELECT agregado,
não imprime tokens/identificadores e não possui opção de escrita. Retenção mínima
é 7 dias. Expiradas há mais de 30 dias são a proposta inicial, não uma política
aprovada. Sessões revogadas ainda não expiradas são preservadas.

A rotina manual em `003_retencao_sessoes.sql` deixa a remoção comentada e usa
lotes de até 500 após autorização. Fixar limite UTC, usar conta de manutenção,
monitorar tempo/locks e confirmar política/backup. DELETE não é reversível por
SQL; ROLLBACK só protege lote ainda não confirmado. Não há EVENT/cron/agendamento.

## Backup e recuperação — procedimento, não execução

Não foi encontrada estratégia de backup automatizada/versionada no código
inspecionado. Binary log está ativo, mas isso não comprova política de retenção,
cópia externa, criptografia, integridade ou recuperação ponto a ponto.

Antes de gerar qualquer cópia real, aprovar destino, janela, RPO/RTO, retenção,
criptografia e responsáveis. Usar diretório 0700, arquivos 0600 e configuração
MySQL privada fora do repositório. Não copiar credenciais para exemplos. Suspender
DDL durante o dump consistente InnoDB; escritas comuns podem continuar com
`--single-transaction`. Usar ferramenta e destino previamente aprovados.

Exemplo a revisar (não executado; depende de ferramentas/configuração existentes):

```bash
umask 077
set -o pipefail
mysqldump --defaults-extra-file=/seguro/mysql-backup.cnf \
  --single-transaction --quick --no-tablespaces --set-gtid-purged=OFF \
  --databases sistema | age --recipient CHAVE_PUBLICA_APROVADA \
  > /destino-privado/sistema.sql.age
```

O pipeline evita arquivo SQL intermediário em claro; verificar código de saída,
tamanho e checksum do arquivo cifrado, sem enviar conteúdo a logs. Validar
privilégios do dump para a versão/opções escolhidas; não desativar mecanismos de
segurança para contornar falhas. Não instalar ferramentas automaticamente.

Restaurar primeiro em **outra instância MySQL 8.4 descartável**, com rede e
credenciais próprias, sem acesso ao servidor real. O dump com `--databases`
contém o nome `sistema`: não basta escolher outro schema no cliente. Revisar
configuração/destino antes de descriptografar em pipeline para `mysql`. Não
reproduzir sessões restauradas em produção nem testar autenticação com pessoas
reais. Comparar schema, contagens, FK, CHECKs, duplicidade e datas por consultas
agregadas e executar testes com dados sintéticos nessa instância.

Recuperação ponto a ponto exige backup-base consistente, coordenadas/GTID
correspondentes e cadeia completa de binlogs preservada/protegida. O comando
acima sozinho não captura esse plano. Definir procedimento separado para obter
coordenadas consistentes e validar reprodução até antes da falha em instância
isolada. Medir RPO/RTO no ensaio. Restauração no banco real exige autorização
específica, plano de corte e validação prévia. Nunca restaurar por tentativa.

## Testes seguros

```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s tests_mysql -v
```

A suíte não lê `.env` nem abre sockets; mocka o Connector e o banco da API.
Verifica SQL/argumentos, falhas, limpeza, atomicidade das chamadas, isolamento de
conexões entre threads, configuração TLS/timeouts, persistência de usuário pela
interface existente e contratos HTTP. FK, expiração e revogação são verificadas
por SQL e respostas simuladas: não provam enforcement de FK/locks/rollback pelo
servidor. Escritas reais, concorrência InnoDB e scripts DDL precisam de instância
descartável, não `sistema`. O `tests/conftest.py` legado depende de SQLAlchemy,
ausente neste ambiente; por isso a nova suíte fica independente em `tests_mysql`.

Referências oficiais: [Connector/Python — opções de conexão](https://dev.mysql.com/doc/connector-python/en/connector-python-connectargs.html)
e [MySQL 8.4 — CHECK](https://dev.mysql.com/doc/refman/8.4/en/create-table-check-constraints.html).
