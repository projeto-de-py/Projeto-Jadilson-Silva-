-- Escopo atual: apenas usuarios e sessoes. Comparar antes de DDL.
CREATE DATABASE IF NOT EXISTS sistema CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE sistema;
CREATE TABLE IF NOT EXISTS sistema.`usuarios` (
  `id` BIGINT UNSIGNED NOT NULL auto_increment,
  `nome` VARCHAR(120) NOT NULL,
  `email` VARCHAR(254) NOT NULL,
  `senha_hash` VARCHAR(255) NOT NULL,
  `perfil` enum('padrao','admin') NOT NULL DEFAULT 'padrao',
  `ativo` TINYINT(1) NOT NULL DEFAULT 1,
  `criado_em` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY uq_usuarios_email (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Tabela tecnica: token aleatorio somente em cookie HttpOnly; banco guarda SHA256.
-- Comparar a estrutura existente antes de executar. Nao substituir tabelas existentes.
CREATE TABLE IF NOT EXISTS sistema.sessoes (
 id_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 usuario_id BIGINT UNSIGNED NOT NULL,
 csrf_token CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 expira_em DATETIME NOT NULL,
 revogada_em DATETIME NULL,
 PRIMARY KEY (id_hash),
 KEY ix_sessoes_usuario (usuario_id),
 KEY ix_sessoes_expiracao (expira_em),
 CONSTRAINT fk_sessoes_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
