-- SOMENTE LEITURA. Revisao 001. Nenhuma correcao automatica de registros.
-- Contagens devem ser zero antes da revisao 002; nao usar mysql --force.
SELECT 'ativo_invalido' AS verificacao, COUNT(*) AS quantidade
FROM sistema.usuarios WHERE ativo NOT IN (0, 1);
SELECT 'expiracao_invalida' AS verificacao, COUNT(*) AS quantidade
FROM sistema.sessoes WHERE expira_em <= criado_em;
SELECT 'revogacao_invalida' AS verificacao, COUNT(*) AS quantidade
FROM sistema.sessoes WHERE revogada_em IS NOT NULL AND revogada_em < criado_em;
SELECT 'sessoes_orfas' AS verificacao, COUNT(*) AS quantidade
FROM sistema.sessoes s LEFT JOIN sistema.usuarios u ON u.id = s.usuario_id
WHERE u.id IS NULL;
SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'sistema' AND TABLE_NAME IN ('usuarios', 'sessoes');
