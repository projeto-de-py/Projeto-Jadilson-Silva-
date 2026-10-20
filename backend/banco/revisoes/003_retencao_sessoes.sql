-- MODELO DESATIVADO. Nao executar exclusao sem autorizacao especifica.
-- Politica proposta: somente sessoes expiradas ha mais de 30 dias, lotes de 500.
-- Nao remove usuarios nem sessoes ainda validas, mesmo se revogadas.
-- Exclusao nao e reversivel por SQL: requer backup autorizado/restauravel.
-- Usar conta de manutencao separada; sistema_app nao possui DELETE.
-- Fixar o mesmo limite UTC em todos os lotes da execucao autorizada.
-- A consulta abaixo e somente leitura e nao retorna identificadores.
SELECT COUNT(*) AS candidatas
FROM sistema.sessoes WHERE expira_em < UTC_TIMESTAMP() - INTERVAL 30 DAY;

-- Apos autorizacao, substituir LIMITE_UTC_FIXO por data UTC revisada.
-- START TRANSACTION;
-- DELETE FROM sistema.sessoes
-- WHERE expira_em < 'LIMITE_UTC_FIXO'
-- ORDER BY expira_em, id_hash LIMIT 500;
-- SELECT ROW_COUNT() AS removidas_no_lote;
-- ROLLBACK; -- default da revisao: nao persistir; COMMIT exige autorizacao.
-- Repeticao manual e limitada, com pausa e monitoramento de locks/replicas.
-- Nao criar EVENT, cron ou tarefa automatica.
