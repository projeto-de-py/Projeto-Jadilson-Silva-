-- Modelo sem senha real: nao executar literalmente.
-- Antes de criar: conferir TODAS as contas sistema_app e seus privilegios.
SELECT User, Host FROM mysql.user WHERE User = 'sistema_app';
-- Se inexistente, criar via conector Python com senha gerada em memoria.
-- CREATE USER 'sistema_app'@'localhost' IDENTIFIED BY '<SENHA_GERADA_EM_MEMORIA>';
-- Para conta nova, conceder somente:
-- GRANT SELECT, INSERT, UPDATE ON sistema.usuarios TO 'sistema_app'@'localhost';
-- GRANT SELECT, INSERT, UPDATE ON sistema.sessoes TO 'sistema_app'@'localhost';
-- Para conta existente, conferir SHOW GRANTS e testar credencial antes de alterar.
-- Nao revogar acessos de outros sistemas nem alterar senha automaticamente.
