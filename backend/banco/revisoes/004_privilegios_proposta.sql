-- PROPOSTA DESATIVADA. Nao cria contas, nao modifica credenciais ou privilegios.
-- Inventariar grants completos e dependencias antes de aprovar uma transicao.
-- Contas devem existir e ter credenciais entregues por canal seguro, fora do SQL.
-- Validar duas credenciais/configuracoes independentes ANTES de reduzir a atual.

-- Backend HTTP (sistema_app):
-- GRANT SELECT ON sistema.usuarios TO 'sistema_app'@'localhost';
-- GRANT SELECT (id_hash,usuario_id,csrf_token,expira_em,revogada_em),
--       INSERT (id_hash,usuario_id,csrf_token,expira_em), UPDATE (revogada_em)
-- ON sistema.sessoes TO 'sistema_app'@'localhost';
-- Remover grants amplos preexistentes exige plano aprovado: grants sao aditivos.
-- No estado auditado, substituir permissao de usuarios exige remover INSERT/UPDATE;
-- em sessoes, retirar grants de tabela e conceder os de coluna na mesma janela.
-- Nao revogar antes de validar o cadastro com sua conta independente.

-- Cadastro administrativo (sistema_cadastro):
-- GRANT INSERT (nome,email,senha_hash,perfil) ON sistema.usuarios
-- TO 'sistema_cadastro'@'localhost';
-- Nao precisa ler hashes, alterar usuarios, consultar sessoes nem conceder grants.

-- Manutencao autorizada (sistema_manutencao):
-- GRANT SELECT (id_hash,expira_em), DELETE ON sistema.sessoes
-- TO 'sistema_manutencao'@'localhost';
-- A credencial de manutencao nao deve estar disponivel no processo HTTP.

-- Reversao da reducao (somente se aprovada e grants iniciais ainda forem os mesmos):
-- GRANT SELECT, INSERT, UPDATE ON sistema.usuarios TO 'sistema_app'@'localhost';
-- GRANT SELECT, INSERT, UPDATE ON sistema.sessoes TO 'sistema_app'@'localhost';
-- Reverter grants novos requer inventario: nao remover contas automaticamente.
