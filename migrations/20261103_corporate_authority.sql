-- Apply once to the same MySQL database used by the Flask panel. No data is copied from ERP/Commerce.
CREATE TABLE IF NOT EXISTS corporate_memberships (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 user_id INT NOT NULL,
 empresa_id INT NOT NULL,
 role VARCHAR(20) NOT NULL DEFAULT 'socio',
 status VARCHAR(12) NOT NULL DEFAULT 'active',
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY uq_corporate_membership (user_id, empresa_id),
 CONSTRAINT fk_corporate_membership_user FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
 CONSTRAINT fk_corporate_membership_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS corporate_systems (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 slug VARCHAR(60) NOT NULL UNIQUE,
 name VARCHAR(120) NOT NULL,
 description VARCHAR(255),
 base_url VARCHAR(500),
 environment VARCHAR(20) NOT NULL DEFAULT 'PRODUCTION',
 status VARCHAR(12) NOT NULL DEFAULT 'inactive',
 icon VARCHAR(80),
 access_policy VARCHAR(20) NOT NULL DEFAULT 'explicit'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS corporate_system_access (
 membership_id BIGINT NOT NULL,
 system_id BIGINT NOT NULL,
 granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY (membership_id, system_id),
 CONSTRAINT fk_corporate_access_membership FOREIGN KEY (membership_id) REFERENCES corporate_memberships(id) ON DELETE CASCADE,
 CONSTRAINT fk_corporate_access_system FOREIGN KEY (system_id) REFERENCES corporate_systems(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS corporate_audit (
 id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 action VARCHAR(50) NOT NULL,
 user_id INT NULL,
 empresa_id INT NULL,
 system_id BIGINT NULL,
 result VARCHAR(20) NOT NULL,
 correlation_id CHAR(32) NOT NULL,
 ip VARCHAR(45),
 user_agent VARCHAR(255),
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 INDEX idx_corporate_audit_time (created_at),
 INDEX idx_corporate_audit_user (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
INSERT IGNORE INTO corporate_systems (slug, name, description, status) VALUES
 ('jp2-business', 'JP2 BUSINESS', 'Centro de controle corporativo', 'active'),
 ('brobond-erp', 'BROBOND ERP', 'Domínio operacional ERP', 'inactive'),
 ('brobond-commerce', 'BROBOND COMMERCE', 'Domínio Commerce', 'inactive'),
 ('brobond-store', 'BROBOND STORE', 'Loja corporativa', 'inactive');
