-- Fase 2 (fundacao de sessao revogavel) — APLICAR MANUALMENTE no MySQL do proprio JP2.
-- Antes: backup testado e execucao em homologacao. Nenhum dado de ERP/Commerce.
-- Nao ha execucao automatica em request/deploy e nao ha credenciais neste arquivo.
-- Requer a migration da Fase 1 (tabela usuarios ja existente no dump do painel).
-- Nome sem prefixo "corporate" para nao alterar o inventario de tabelas da Fase 1.
CREATE TABLE IF NOT EXISTS jp2_sessions (
 sid_hash CHAR(64) NOT NULL PRIMARY KEY,
 user_id INT NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 expires_at DATETIME NOT NULL,
 revoked_at DATETIME NULL,
 revoke_reason VARCHAR(60) NULL,
 INDEX idx_jp2_sessions_user (user_id, revoked_at),
 INDEX idx_jp2_sessions_expiry (expires_at),
 CONSTRAINT fk_jp2_sessions_user FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
