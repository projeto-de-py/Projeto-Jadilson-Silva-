-- PENDENTE DE AUTORIZACAO. Reverte apenas CHECKs da revisao 002.
-- Consultar information_schema antes: executar somente etapas existentes.
-- Nao usar --force. DROP CHECK nao restaura valores nem desfaz outras revisoes.
ALTER TABLE sistema.sessoes
  DROP CHECK chk_sessoes_expiracao,
  DROP CHECK chk_sessoes_revogacao;
ALTER TABLE sistema.usuarios DROP CHECK chk_usuarios_ativo;
