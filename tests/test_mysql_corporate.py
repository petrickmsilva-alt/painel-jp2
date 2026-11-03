"""MySQL integration suite. Only runs on an explicitly opted-in LOCAL disposable server.

CI sets JP2_TEST_MYSQL_ISOLATED=1 and JP2_REQUIRE_MYSQL=1. A unique schema is
created and dropped; never point this at a production server.
"""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pymysql

os.environ.setdefault('FLASK_SECRET_KEY', 'local-tests-not-a-production-secret')
os.environ.setdefault('FLASK_COOKIE_SECURE', 'false')


class MySQLCorporateTests(unittest.TestCase):
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
                                    user=os.environ['JP2_TEST_MYSQL_USER'], password=os.environ['JP2_TEST_MYSQL_PASSWORD'],
                                    autocommit=True, cursorclass=pymysql.cursors.DictCursor)
        with cls.admin.cursor() as cur:
            cur.execute(f'CREATE DATABASE `{cls.schema}` CHARACTER SET utf8mb4')
        cls.original_env = {key: os.environ.get(key) for key in ('DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME')}
        os.environ.update(DB_HOST=host, DB_USER=os.environ['JP2_TEST_MYSQL_USER'],
                          DB_PASSWORD=os.environ['JP2_TEST_MYSQL_PASSWORD'], DB_NAME=cls.schema)
        try:
            cls.db = pymysql.connect(host=host, port=int(os.environ.get('JP2_TEST_MYSQL_PORT', '3306')),
                                     user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'],
                                     database=cls.schema, autocommit=True, cursorclass=pymysql.cursors.DictCursor)
            with cls.db.cursor() as cur:
                # The actual dump declares signed INT(11) PKs, unique usuario and InnoDB.
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
        sql = (Path(__file__).resolve().parents[1] / 'migrations/20261103_corporate_authority.sql').read_text()
        # No stored procedures or semicolons inside strings in this migration.
        with cls.db.cursor() as cur:
            for statement in sql.split(';'):
                statement = '\n'.join(line for line in statement.splitlines() if not line.strip().startswith('--')).strip()
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
        self.app = app
        self.client = self.new_client()
        with self.db.cursor() as cur:
            cur.execute('DELETE FROM corporate_audit')
            cur.execute('DELETE FROM corporate_system_access')
            cur.execute('DELETE FROM corporate_memberships')
            cur.execute("UPDATE corporate_systems SET status='inactive' WHERE slug IN ('brobond-erp','brobond-commerce')")

    def new_client(self, username='governor', company=100):
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['usuario_logado'] = username
            sess['perfil_usuario'] = 'admin'  # DB role is authoritative, not this cookie
            sess['corporate_empresa_id'] = company
            sess['_csrf_token'] = 'isolated-test-csrf'
        return client

    def post(self, action, **kwargs):
        return self.client.post('/admin/acessos', data={'action': action, '_csrf_token': 'isolated-test-csrf', **kwargs})

    def count(self, table, where='1=1'):
        assert table in ('corporate_audit', 'corporate_memberships', 'corporate_system_access')
        with self.db.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) AS n FROM {table} WHERE {where}')
            return cur.fetchone()['n']

    def membership(self, role='socio', status='active', user_id='2', empresa_id='100'):
        return self.post('membership', user_id=user_id, empresa_id=empresa_id, role=role, status=status)

    def access(self, grant='yes', user_id='2', empresa_id='100', slug='brobond-erp'):
        return self.post('access', user_id=user_id, empresa_id=empresa_id, slug=slug, grant=grant)

    def test_schema_replay_fk_seeds_and_integrity(self):
        self.migrate()  # re-execution must preserve data and seeds
        with self.db.cursor() as cur:
            cur.execute("SELECT table_name, engine FROM information_schema.tables WHERE table_schema=%s AND table_name LIKE 'corporate%%'", (self.schema,))
            self.assertEqual({r['table_name'] for r in cur.fetchall()},
                             {'corporate_memberships', 'corporate_systems', 'corporate_system_access', 'corporate_audit'})
            cur.execute("SELECT constraint_name FROM information_schema.referential_constraints WHERE constraint_schema=%s AND table_name LIKE 'corporate%%'", (self.schema,))
            self.assertEqual(len(cur.fetchall()), 4)
            cur.execute("SELECT column_name,column_type FROM information_schema.columns WHERE table_schema=%s AND table_name='usuarios' AND column_name='id'", (self.schema,))
            self.assertRegex(cur.fetchone()['column_type'], r'^int(\(11\))?$')
            cur.execute("SELECT column_name,column_type FROM information_schema.columns WHERE table_schema=%s AND table_name='empresas' AND column_name='id'", (self.schema,))
            self.assertRegex(cur.fetchone()['column_type'], r'^int(\(11\))?$')
            cur.execute('SELECT slug,status FROM corporate_systems ORDER BY slug')
            self.assertEqual(len(cur.fetchall()), 4)
            with self.assertRaises(pymysql.err.IntegrityError):
                cur.execute('INSERT INTO corporate_memberships (user_id,empresa_id) VALUES (9999,100)')

    def test_create_role_revoke_grant_duplicate_and_tenant_isolation(self):
        self.assertEqual(self.membership().status_code, 302)
        self.assertEqual(self.membership(role='leitura').status_code, 302)
        self.assertEqual(self.count('corporate_memberships'), 1)
        self.assertEqual(self.access().status_code, 302)
        self.assertEqual(self.access().status_code, 302)
        self.assertEqual(self.count('corporate_system_access'), 1)
        # System inactive means not visible even with grant; only active and entitled is returned.
        employee = self.new_client('employee', 100)
        self.assertEqual(employee.get('/api/corporate/systems').json['systems'], [])
        self.assertEqual(self.post('system', slug='brobond-erp', status='active', environment='PRODUCTION', base_url='').status_code, 302)
        self.assertEqual([s['slug'] for s in employee.get('/api/corporate/systems').json['systems']], ['brobond-erp'])
        other_company = self.new_client('employee', 200)
        self.assertEqual(other_company.get('/api/corporate/systems').json['systems'], [])
        self.assertEqual(other_company.get('/api/corporate/me').json['company'], None)
        self.assertEqual(self.access(grant='no').status_code, 302)
        self.assertEqual(self.count('corporate_system_access'), 0)
        self.assertEqual(self.membership(status='revoked').status_code, 302)
        self.assertEqual(self.access().status_code, 400)
        self.assertEqual(employee.get('/api/corporate/systems').json['systems'], [])
        self.assertGreaterEqual(self.count('corporate_audit'), 6)

    def test_invalid_resources_csrf_origin_and_no_escalation(self):
        self.assertEqual(self.membership(user_id='9999').status_code, 400)
        self.assertEqual(self.membership(empresa_id='9999').status_code, 400)
        self.assertEqual(self.membership().status_code, 302)
        self.assertEqual(self.access(slug='missing-system').status_code, 400)
        self.assertEqual(self.post('system', slug='missing-system', status='active', environment='PRODUCTION').status_code, 400)
        self.assertEqual(self.client.post('/admin/acessos', data={'action': 'membership'}).status_code, 403)
        self.assertEqual(self.client.post('/admin/acessos', headers={'Origin': 'https://attacker.example'},
                                          data={'action': 'membership', '_csrf_token': 'isolated-test-csrf'}).status_code, 403)
        employee = self.new_client('employee')
        self.assertEqual(employee.get('/admin/acessos').status_code, 403)
        self.assertEqual(employee.post('/admin/acessos', data={'action': 'access', '_csrf_token': 'isolated-test-csrf'}).status_code, 403)
        with self.db.cursor() as cur:
            cur.execute("UPDATE usuarios SET perfil='socio' WHERE id=1")
        try:
            self.assertEqual(self.client.get('/admin/acessos').status_code, 403)
        finally:
            with self.db.cursor() as cur:
                cur.execute("UPDATE usuarios SET perfil='admin' WHERE id=1")
        self.assertEqual(self.count('corporate_memberships'), 1)

    def test_audit_failure_rolls_back_grant_membership_and_system(self):
        import corporate
        with patch.object(corporate, 'audit', side_effect=RuntimeError('injected audit failure')):
            self.assertEqual(self.membership().status_code, 500)
        self.assertEqual(self.count('corporate_memberships'), 0)
        self.assertEqual(self.membership().status_code, 302)
        with patch.object(corporate, 'audit', side_effect=RuntimeError('injected audit failure')):
            self.assertEqual(self.access().status_code, 500)
            self.assertEqual(self.post('system', slug='brobond-erp', status='active', environment='PRODUCTION').status_code, 500)
        self.assertEqual(self.count('corporate_system_access'), 0)
        with self.db.cursor() as cur:
            cur.execute("SELECT status FROM corporate_systems WHERE slug='brobond-erp'")
            self.assertEqual(cur.fetchone()['status'], 'inactive')
        self.assertEqual(self.count('corporate_audit'), 1)

    def test_two_simultaneous_grants_are_idempotent(self):
        self.assertEqual(self.membership().status_code, 302)
        def grant(_):
            client = self.new_client()
            return client.post('/admin/acessos', data={'action': 'access', 'user_id': '2', 'empresa_id': '100',
                              'slug': 'brobond-erp', 'grant': 'yes', '_csrf_token': 'isolated-test-csrf'}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(grant, range(2))), [302, 302])
        self.assertEqual(self.count('corporate_system_access'), 1)
        self.assertEqual(self.count('corporate_audit'), 3)  # membership + two idempotent requests
