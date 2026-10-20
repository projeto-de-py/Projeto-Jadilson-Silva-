-- PENDENTE DE AUTORIZACAO. MySQL 8.4. Nao executado.
-- Precondicoes: revisao 001 sem inconsistencias, nomes abaixo livres,
-- backup/restauracao validados e janela aprovada para metadata locks/validacao.
-- DDL causa commit implicito: cada ALTER e uma etapa, nao uma transacao conjunta.
-- Se o segundo ALTER falhar, registrar que somente a primeira etapa foi aplicada.
-- Nao corrige dados, nao recria tabelas, nao adiciona indices.
ALTER TABLE sistema.usuarios
  ADD CONSTRAINT chk_usuarios_ativo CHECK (ativo IN (0, 1));
ALTER TABLE sistema.sessoes
  ADD CONSTRAINT chk_sessoes_expiracao CHECK (expira_em > criado_em),
  ADD CONSTRAINT chk_sessoes_revogacao
    CHECK (revogada_em IS NULL OR revogada_em >= criado_em);
