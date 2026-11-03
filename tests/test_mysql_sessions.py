"""Fase 2 MySQL integration. Only on an explicitly opted-in LOCAL disposable server.

CI sets JP2_TEST_MYSQL_ISOLATED=1 and JP2_REQUIRE_MYSQL=1. A unique schema is
created and dropped; never point this at a homologation/production server.
"""
import hashlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pymysql

os.environ.setdefault('FLASK_SECRET_KEY', 'local-tests-not-a-production-secret')
os.environ.setdefault('FLASK_COOKIE_SECURE', 'false')

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ('migrations/20261103_corporate_authority.sql',
              'migrations/20261104_revocable_sessions.sql')


def digest(sid):
    return hashlib.sha256(sid.encode('utf-8')).hexdigest()


class MySQLSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        host = os.environ.get('JP2_TEST_MYSQL_HOST')
        allowed = os.environ.get('JP2_TEST_MYSQL_ISOLATED') == '1' and host in ('127.0.0.1', 'localhost')
        if not allowed:
            if os.environ.get('JP2_REQUIRE_MYSQL') == '1':
                raise RuntimeError('MySQL integration required: isolated local test server not configured')
            raise unittest.SkipTest('isolated local MySQL test server not configured')
        cls.schema = 'jp2_ci_' + uuid4().hex[:12]
        cls.admin = pymysql.connect(host=host, port=int(os.environ.get('JP2_TEST_MYSQL_PORT', '3306')),
                                    user=os.environ['JP2_TEST_MYSQL_USER'],
                                    password=os.environ['JP2_TEST_MYSQL_PASSWORD'],
                                    autocommit=True, cursorclass=pymysql.cursors.DictCursor)
        with cls.admin.cursor() as cur:
            cur.execute(f'CREATE DATABASE `{cls.schema}` CHARACTER SET utf8mb4')
        cls.original_env = {key: os.environ.get(key) for key in ('DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME')}
        os.environ.update(DB_HOST=host, DB_USER=os.environ['JP2_TEST_MYSQL_USER'],
                          DB_PASSWORD=os.environ['JP2_TEST_MYSQL_PASSWORD'], DB_NAME=cls.schema)
        try:
            cls.db = pymysql.connect(host=host, port=int(os.environ.get('JP2_TEST_MYSQL_PORT', '3306')),
                                     user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'],
                                     database=cls.schema, autocommit=True,
                                     cursorclass=pymysql.cursors.DictCursor)
            with cls.db.cursor() as cur:
                # Tipos/engine minimos reproduzidos do dump do painel, sem dados reais.
                cur.execute('''CREATE TABLE usuarios (id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
                                usuario VARCHAR(100) NOT NULL UNIQUE, senha VARCHAR(255) NOT NULL,
                                nome_exibicao VARCHAR(100), perfil VARCHAR(20) NOT NULL DEFAULT 'socio') ENGINE=InnoDB''')
                cur.execute('''CREATE TABLE empresas (id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
                                nome VARCHAR(255) NOT NULL, cnpj VARCHAR(20), ramo_atividade VARCHAR(100)) ENGINE=InnoDB''')
                cur.execute('INSERT INTO usuarios (id,usuario,senha,perfil) VALUES (1,%s,%s,%s),(2,%s,%s,%s)',
                            ('governor', 'test-hash', 'admin', 'employee', 'test-hash', 'socio'))
                cur.execute('INSERT INTO empresas (id,nome) VALUES (100,%s),(200,%s)', ('Empresa A', 'Empresa B'))
            cls.migrate()
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def migrate(cls):
        for name in MIGRATIONS:
            sql = (ROOT / name).read_text()
            with cls.db.cursor() as cur:
                for statement in sql.split(';'):
                    statement = '\n'.join(line for line in statement.splitlines()
                                          if not line.strip().startswith('--')).strip()
                    if statement:
                        cur.execute(statement)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'admin'):
            with cls.admin.cursor() as cur:
                cur.execute(f'DROP DATABASE IF EXISTS `{cls.schema}`')
            cls.admin.close()
        if hasattr(cls, 'db'):
            cls.db.close()
        for key, value in getattr(cls, 'original_env', {}).items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def setUp(self):
        from app import app
        import revocable_sessions as rs
        self.app = app
        self.rs = rs
        with self.db.cursor() as cur:
            cur.execute('DELETE FROM jp2_sessions')
            cur.execute('DELETE FROM corporate_audit')
            cur.execute('DELETE FROM corporate_system_access')
            cur.execute('DELETE FROM corporate_memberships')
            cur.execute("INSERT INTO corporate_memberships (user_id, empresa_id, role, status) "
                        "VALUES (1, 100, 'socio', 'active')")

    def client(self, sid=None, company=100):
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['usuario_logado'] = 'governor'
            sess['corporate_empresa_id'] = company
            sess['_csrf_token'] = 'isolated-test-csrf'
            if sid is not None:
                sess[self.rs.COOKIE_KEY] = sid
        return client

    def test_migration_idempotente_preserva_invariantes_da_fase1(self):
        self.migrate()  # replay nao pode duplicar seeds, dados ou tabelas
        with self.db.cursor() as cur:
            # MySQL 8 devolve colunas de information_schema em maiusculas: usar alias.
            cur.execute("SELECT engine AS engine_name FROM information_schema.tables "
                        "WHERE table_schema=%s AND table_name='jp2_sessions'", (self.schema,))
            self.assertEqual(cur.fetchone()['engine_name'], 'InnoDB')
            cur.execute("SELECT column_type AS column_type_name FROM information_schema.columns "
                        "WHERE table_schema=%s AND table_name='jp2_sessions' AND column_name='sid_hash'",
                        (self.schema,))
            self.assertEqual(cur.fetchone()['column_type_name'].lower(), 'char(64)')
            cur.execute("SELECT COUNT(*) AS n FROM information_schema.referential_constraints "
                        "WHERE constraint_schema=%s AND table_name='jp2_sessions'", (self.schema,))
            self.assertEqual(cur.fetchone()['n'], 1)
            cur.execute("SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema=%s "
                        "AND table_name LIKE 'corporate%%'", (self.schema,))
            self.assertEqual(cur.fetchone()['n'], 4)
            cur.execute('SELECT COUNT(*) AS n FROM jp2_sessions')
            self.assertEqual(cur.fetchone()['n'], 0)
            cur.execute('SELECT COUNT(*) AS n FROM corporate_systems')
            self.assertEqual(cur.fetchone()['n'], 4)

    def test_issue_validate_revoke_expiracao_revogacao_e_cascade(self):
        sid = self.rs.issue(self.db, 1)
        self.assertEqual(self.rs.validate(self.db, sid)['user_id'], 1)
        with self.db.cursor() as cur:
            cur.execute('SELECT COUNT(*) AS n FROM jp2_sessions WHERE sid_hash=%s', (sid,))
            self.assertEqual(cur.fetchone()['n'], 0)  # handle bruto nunca persistido
        self.assertEqual(self.rs.revoke(self.db, sid, 'admin'), 1)
        self.assertIsNone(self.rs.validate(self.db, sid))

        expirado = self.rs.issue(self.db, 2)
        with self.db.cursor() as cur:
            cur.execute('UPDATE jp2_sessions SET expires_at=DATE_SUB(NOW(), INTERVAL 1 MINUTE) '
                        'WHERE sid_hash=%s', (digest(expirado),))
        self.assertIsNone(self.rs.validate(self.db, expirado))

        vivo = self.rs.issue(self.db, 2)
        self.assertGreaterEqual(self.rs.revoke_user(self.db, 2, 'membership_revoked'), 1)
        self.assertIsNone(self.rs.validate(self.db, vivo))

        with self.db.cursor() as cur:
            cur.execute("INSERT INTO usuarios (id,usuario,senha,perfil) VALUES (3,'temp','x','leitura')")
        temporario = self.rs.issue(self.db, 3)
        with self.db.cursor() as cur:
            cur.execute('DELETE FROM usuarios WHERE id=3')
            cur.execute('SELECT COUNT(*) AS n FROM jp2_sessions WHERE sid_hash=%s', (digest(temporario),))
            self.assertEqual(cur.fetchone()['n'], 0)  # FK ON DELETE CASCADE

    def test_gate_com_mysql_real_nega_contexto_invalido_e_rota_global(self):
        with patch.dict(os.environ, {'JP2_ENFORCE_CORPORATE_CONTEXT': '1'}):
            client = self.client()
            self.assertEqual(client.get('/carteira-investimentos').status_code, 302)
            self.assertEqual(client.get('/carteira-investimentos?empresa_id=200').status_code, 403)
            self.assertEqual(client.get('/api/empresas').status_code, 403)
            with self.db.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS n FROM corporate_audit "
                            "WHERE action='LEGACY_CONTEXT_DENIED' AND result='denied'")
                self.assertEqual(cur.fetchone()['n'], 2)
            with self.db.cursor() as cur:
                cur.execute("UPDATE corporate_memberships SET status='revoked' WHERE user_id=1")
            self.assertEqual(client.get('/carteira-investimentos').status_code, 403)

    def test_hook_de_sessao_com_mysql_real_revoga_cookie_valido(self):
        with patch.dict(os.environ, {'JP2_REVOCABLE_SESSIONS': '1'}):
            sess = {}
            self.rs.registrar_sessao_apos_login({'id': 1}, sess)
            self.assertIsNotNone(self.rs.validate(self.db, sess[self.rs.COOKIE_KEY]))

            client = self.client(sess[self.rs.COOKIE_KEY])
            permitido = client.get('/carteira-investimentos')
            self.assertEqual(permitido.status_code, 302)
            self.assertIn('/carteira', permitido.headers['Location'])

            self.rs.revoke_user(self.db, 1, 'admin')
            encerrado = client.get('/carteira-investimentos')
            self.assertEqual(encerrado.status_code, 302)
            self.assertIn('/login', encerrado.headers['Location'])
            self.assertEqual(self.client().get('/api/performance-status').status_code, 401)
