# Relatório do aprimoramento MySQL — 20/10/2026

## 1. Estado inicial confirmado

Branch `integracao/mysql-autenticacao`, HEAD `7dbda0a`, árvore inicialmente limpa.
A referência local `origin/main` coincide com o HEAD; não houve fetch, merge,
commit ou push. MySQL 8.4.11 ativo em 127.0.0.1:3306, banco `sistema`, conta
`sistema_app@localhost`, InnoDB, utf8mb4_unicode_ci e isolamento REPEATABLE READ.
General log desativado, binary log ativo. TLS 1.3 negociado na conexão auditada,
sem prova de validação de certificado/identidade na configuração anterior.
`.env` com modo 0600 e ignorado pelo Git; conteúdo sensível não foi publicado.

Há 1 usuário e 3 sessões; contagens agregadas iniciais e finais coincidem.
Zero usuários inválidos nas verificações de identificador, nome, e-mail aparado,
perfil e ativação; zero e-mails duplicados, sessões órfãs, datas incoerentes e
identificadores/CSRF fora do formato hexadecimal de 64 caracteres. Não houve
correção de registros, escrita de teste, autenticação ou logout no banco real.
Essas contagens não são prova criptográfica de imutabilidade de todo o banco;
a preservação decorre também de somente SELECT/EXPLAIN terem sido executados.

Estrutura consultada:

| Tabela | Colunas |
|---|---|
| usuarios | id BIGINT UNSIGNED PK AUTO_INCREMENT; nome VARCHAR(120); email VARCHAR(254) UNIQUE; senha_hash VARCHAR(255); perfil ENUM('padrao','admin') DEFAULT padrao; ativo TINYINT(1) DEFAULT 1; criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP; atualizado_em TIMESTAMP com atualização automática |
| sessoes | id_hash CHAR(64) ascii_bin PK; usuario_id BIGINT UNSIGNED FK; csrf_token CHAR(64) ascii_bin; criado_em DATETIME DEFAULT CURRENT_TIMESTAMP; expira_em DATETIME; revogada_em DATETIME NULL |

Todas as colunas são NOT NULL, exceto revogada_em. FK para usuarios.id com
RESTRICT em alteração/exclusão. Índices uq_usuarios_email, ix_sessoes_usuario,
ix_sessoes_expiracao e PKs existentes. Não havia CHECKs. Grants reais: SELECT,
INSERT e UPDATE nas duas tabelas, sem GRANT OPTION/DELETE/DDL exibidos.

## 2. Problemas encontrados

- Revogar sessão antiga e inserir nova usava duas conexões/commits; falha de
  inserção podia deixar o cliente sem a sessão anterior.
- Rollback ou close com falha podiam ocultar a causa original; close após commit
  confirmado podia produzir falha aparente de uma escrita bem-sucedida.
- Só havia timeout de conexão, sem limites de leitura/escrita explícitos.
- Configuração não permitia exigir CA e identidade TLS para banco remoto.
- Conta compartilhada HTTP/cadastro tem privilégios maiores que os do HTTP.
- Não havia política operacional de retenção/backup/ensaio de restauração no
  código inspecionado; binlog ativo não comprova recuperabilidade.
- Testes legados carregam conftest SQLAlchemy, ausente no ambiente atual, e os
  testes reais existentes escrevem em sistema: não são adequados a esta missão.

## 3. Correções e arquivos

Alterados:

- `backend/database.py`: SQL parametrizado centralizado, transação única para
  substituição de sessão, leituras READ ONLY, cursor buffered para leitura,
  UTC/utf8mb4 explícitos, timeouts, configuração TLS e limpeza robusta.
- `backend/config.py`: opções MySQL de timeout/CA, limites e validação de CA para
  host remoto de produção; credenciais atuais e defaults locais preservados.
- `backend/main.py`: somente duas linhas de integração da persistência, passando
  o hash anterior a create_session; rotas e contratos HTTP preservados.
- `backend/requirements.txt`: mínimo do Connector elevado de 9 para 9.2, versão
  que suporta read_timeout/write_timeout; lock existente permanece compatível.

Criados:

- `backend/tests_mysql/test_persistencia.py`: 32 testes isolados.
- `backend/banco/retencao_sessoes.py`: planejamento exclusivamente SELECT,
  retenção validada, saída agregada sem identificadores e sem opção de escrita.
- `backend/banco/conexao.env.example`: somente novas opções não sensíveis.
- `backend/banco/revisoes/001_pre_validacao.sql`.
- `backend/banco/revisoes/002_checks.up.sql` e `002_checks.down.sql`.
- `backend/banco/revisoes/003_retencao_sessoes.sql`.
- `backend/banco/revisoes/004_privilegios_proposta.sql`.
- `backend/banco/OPERACAO_MYSQL.md` e este relatório.

Não foram alterados frontend, dashboard, design, rotas, schemas HTTP, Argon2id,
credenciais, configuração real .env, esquema real ou módulos de negócio.
Não foram instaladas dependências, gerados backups ou executadas migrações.

## 4. Segurança, consultas e desempenho

Consultas permanecem parametrizadas; nenhum valor externo é interpolado no SQL.
Logs de limpeza não incluem erro bruto, parâmetros ou credenciais. Erros MySQL
continuam recebendo a resposta genérica 503 já existente no backend.
Com MYSQL_SSL_CA são exigidas validação de certificado e identidade; produção
remota sem CA é rejeitada. Sem CA, a negociação local anterior é mantida.

EXPLAIN real da busca de e-mail existente usou uq_usuarios_email, acesso const,
estimativa de uma linha. A busca completa de sessão foi simplificada pelo
otimizador para Impossible WHERE após leitura de tabelas const no estado atual;
não há evidência de varredura, nem uma amostra de sessão ativa para medir seu
plano completo. EXPLAIN da seleção por expiração utilizou ix_sessoes_expiracao,
acesso range e Using index. Não há fundamento para novos índices neste volume.
Não houve benchmark de carga ou alegação de ganho de latência medido.

Troca de sessão elimina uma conexão e um commit em relação ao fluxo anterior,
confirmado pela estrutura das chamadas nos testes. Não houve adição de pool ou
retry de escrita, evitando replay quando resultado do COMMIT é desconhecido.
Leitura READ ONLY acrescenta comandos de transação: o efeito líquido em latência
precisa ser medido em carga isolada antes de outra otimização.

## 5. Transações e sessões

Revogação anterior e criação nova usam um commit. Erro no INSERT/commit tenta
rollback, preserva o erro e fecha conexão. Testes simulam falhas de FK,
duplicidade, conexão perdida e cleanup. Conexões não são compartilhadas entre
threads; operação posterior abre nova conexão após falha anterior.
Identificador bruto continua somente no cookie HttpOnly; MySQL recebe SHA256.
CSRF, expiração, usuário ativo e revogação permanecem no fluxo existente.

Não há garantia de sessão única: dois logins concorrentes podem criar sessões
independentes. Tests com mocks não provam locks/rollback InnoDB; esse ensaio
precisa de instância descartável. Alteração de senha não revoga automaticamente
todas as sessões existentes; essa política permanece pendente de definição.

## 6. Testes executados e resultados

Comando seguro, sem cache/bytecode e sem acesso ao banco:

`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s tests_mysql -v`

Resultado: **32 testes passaram**. Cobrem parâmetros/SQL Injection, conexão,
leitura READ ONLY, cursores, UTC/charset/timeouts, TLS, rollback, cleanup,
commit incerto sem replay, nova conexão após falha, persistência de usuários
pela interface execute, sessões, FK/duplicidade simuladas, concorrência de
conexões, retenção somente leitura e contratos de login/restauração/logout.

Os testes HTTP usam banco falso e verificação de senha mockada: verificam a
integração de persistência e o contrato; não certificam Argon2id ou MySQL real.
Há aviso de depreciação do TestClient/httpx da dependência já instalada; não
foram alteradas dependências para ocultá-lo.

Consultas reais com a nova Database confirmaram conexão, negociação TLS 1.3,
SELECT de usuário inexistente, SELECT de sessão inexistente, EXPLAIN e preview
de retenção: zero candidatas para a política proposta de 30 dias. Nenhum dado
pessoal, identificador ou hash foi impresso. A variável @@transaction_read_only
consultada mostra o default da sessão, não valida o acesso da transação corrente;
a chamada readonly=True foi validada por mocks/implementação do Connector, sem
tentar escrita no banco real.

Sintaxe dos cinco arquivos Python novos/modificados verificada via AST sem gerar
arquivos. `git diff --check` sem erros. Diff inspecionado e status conferido.
Nenhuma alteração sob frontend. Não executados: suíte real que cria/exclui
registros, DDL, concessão/revogação, backup, restore ou limpeza efetiva.

## 7. Scripts preparados e pendências de autorização

- 001: pré-validação somente leitura.
- 002 up/down: três CHECKs e reversão de esquema, ainda não aplicados. Validar
  nomes/dados/locks em instância isolada, obter autorização e backup restaurável.
  DDL tem commit implícito: reversão exige etapas explícitas, inclusive em falha
  parcial; não altera dados nem adiciona índices.
- 003: SELECT de contagem e exclusão em lotes totalmente comentada. Qualquer
  DELETE é irreversível após COMMIT sem backup; não chamar de migração reversível.
- 004: proposta comentada de contas/privilégios HTTP, cadastro e manutenção.
  Não cria usuários ou contém senhas. Grants menores são aditivos e exigem retirar
  os amplos em transição aprovada, com cadastro já usando credencial própria.

Permanecem pendentes: aplicar/reverter CHECKs, provisionar contas, reduzir grants,
alterar credenciais/configuração reais, executar retenção, gerar backup e
restaurar. Nenhuma dessas ações foi necessária para concluir as melhorias locais.

## 8. Backup, recuperação e produção

`OPERACAO_MYSQL.md` prepara backup consistente InnoDB, criptografia por pipeline,
permissões privadas, validação de códigos/checksum, restauração em outra instância
MySQL 8.4 e verificação de integridade. Também distingue dump de plano de PITR:
este exige coordenadas consistentes e cadeia de binlogs. Nenhum ensaio real ou
cópia com dados reais foi produzido. RPO/RTO e retenção precisam ser aprovados.

Prioridades antes de produção: ensaiar escrita/concorrência/DDL em ambiente
descartável; separar contas HTTP/cadastro; validar TLS com CA e casos negativos;
aplicar CHECKs após autorização; testar backup/restauração e recuperação com
binlogs; definir retenção, capacidade e monitoramento sem conteúdo sensível.
Rate limit em memória e implementação JWT paralela continuam fora desta entrega.
A camada está mais testável e robusta, mas esta entrega não certifica produção.

Fontes oficiais consultadas: [opções de conexão do Connector/Python](https://dev.mysql.com/doc/connector-python/en/connector-python-connectargs.html)
e [CHECK constraints no MySQL 8.4](https://dev.mysql.com/doc/refman/8.4/en/create-table-check-constraints.html).
