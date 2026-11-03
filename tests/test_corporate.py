"""Isolated Flask route/security tests. No production MySQL or external services."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('FLASK_SECRET_KEY', 'local-tests-not-a-production-secret')
os.environ.setdefault('FLASK_COOKIE_SECURE', 'false')
from app import app
from corporate import safe_system_url


class Cursor:
    def __init__(self, state):
        self.state = state
        self.one = None
        self.many = []
        self.rowcount = 1

    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, sql, params=()):
        self.one = None
        self.many = []
        if 'FROM usuarios WHERE usuario' in sql:
            self.one = self.state['users'].get(params[0])
        elif 'FROM corporate_memberships m JOIN empresas' in sql:
            self.many = [m for m in self.state['members'] if m['user_id'] == params[0] and m['active']]
        elif 'FROM corporate_systems s JOIN corporate_system_access' in sql:
            self.many = [dict(s) for s in self.state['systems'] if s['member_id'] == params[0] and s['active']]
        elif 'INSERT INTO corporate_audit' in sql:
            self.state['audits'].append(params)
        else:
            raise AssertionError('Unexpected query: ' + sql)
    def fetchone(self): return self.one
    def fetchall(self): return self.many


class Connection:
    def __init__(self, state): self.state = state
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def cursor(self): return Cursor(self.state)


class CorporateTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            'users': {'alice': {'id': 1, 'usuario': 'alice', 'nome_exibicao': 'Alice', 'perfil': 'socio'},
                      'bob': {'id': 2, 'usuario': 'bob', 'nome_exibicao': 'Bob', 'perfil': 'leitura'}},
            'members': [{'id': 10, 'user_id': 1, 'empresa_id': 100, 'role': 'socio', 'company_name': 'A', 'active': True},
                        {'id': 20, 'user_id': 2, 'empresa_id': 200, 'role': 'leitura', 'company_name': 'B', 'active': True}],
            'systems': [{'id': 1, 'member_id': 10, 'slug': 'jp2-business', 'name': 'JP2 BUSINESS', 'description': '', 'environment': 'PRODUCTION', 'active': True},
                        {'id': 2, 'member_id': 10, 'slug': 'brobond-erp', 'name': 'BROBOND ERP', 'description': '', 'environment': 'PRODUCTION', 'active': False},
                        {'id': 3, 'member_id': 20, 'slug': 'brobond-commerce', 'name': 'BROBOND COMMERCE', 'description': '', 'environment': 'PRODUCTION', 'active': True}],
            'audits': []}
        self.mock = patch('corporate.get_db_connection', side_effect=lambda: Connection(self.state))
        self.mock.start()
        self.addCleanup(self.mock.stop)
        admin_mock = patch('app.usuario_atual_e_admin', return_value=False)
        admin_mock.start()
        self.addCleanup(admin_mock.stop)
        self.client = app.test_client()

    def login(self, username='alice', company=100):
        with self.client.session_transaction() as sess:
            sess['usuario_logado'] = username
            sess['corporate_empresa_id'] = company
            sess['_csrf_token'] = 'test-csrf'

    def test_anonymous_denied(self):
        self.assertEqual(self.client.get('/api/corporate/me').status_code, 401)
        self.assertEqual(self.client.get('/api/corporate/systems').status_code, 401)

    def test_tenant_isolation_and_context_change(self):
        self.login()
        self.assertEqual(self.client.get('/api/corporate/me').json['company']['id'], 100)
        response = self.client.post('/sistemas/contexto', data={'empresa_id': 200, '_csrf_token': 'test-csrf'})
        self.assertEqual(response.status_code, 403)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess['corporate_empresa_id'], 100)
            sess['corporate_empresa_id'] = 200  # forged/stale context is checked against DB
        self.assertIsNone(self.client.get('/api/corporate/me').json['company'])
        self.assertEqual(self.client.get('/api/corporate/systems').json['systems'], [])
        self.assertEqual(self.client.get('/sistemas/brobond-commerce').status_code, 404)

    def test_context_switch_and_membership_revocation(self):
        self.state['members'].append({'id': 30, 'user_id': 1, 'empresa_id': 200,
                                      'role': 'leitura', 'company_name': 'B', 'active': True})
        self.login()
        response = self.client.post('/sistemas/contexto',
                                    data={'empresa_id': 200, '_csrf_token': 'test-csrf'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get('/api/corporate/me').json['company']['id'], 200)
        self.assertEqual(self.client.get('/api/corporate/systems').json['systems'], [])
        self.state['members'][2]['active'] = False
        self.assertIsNone(self.client.get('/api/corporate/me').json['company'])
        self.assertEqual(self.client.get('/api/corporate/systems').json['systems'], [])

    def test_erp_and_commerce_denied_without_active_access(self):
        self.login()
        self.assertEqual([s['slug'] for s in self.client.get('/api/corporate/systems').json['systems']], ['jp2-business'])
        self.assertEqual(self.client.get('/sistemas/brobond-erp').status_code, 404)
        self.assertEqual(self.client.get('/sistemas/brobond-commerce').status_code, 404)
        self.state['systems'][1]['active'] = True
        self.assertEqual(self.client.get('/sistemas/brobond-erp').status_code, 200)
        self.state['members'][0]['active'] = False
        self.assertEqual(self.client.get('/sistemas/brobond-erp').status_code, 404)

    def test_role_rechecked_and_csrf_enforced(self):
        self.login()
        self.assertEqual(self.client.get('/admin/acessos').status_code, 403)
        self.assertEqual(self.client.post('/sistemas/contexto', data={'empresa_id': 100}).status_code, 403)
        self.state['users'].pop('alice')
        self.assertEqual(self.client.get('/api/corporate/me').status_code, 401)

    def test_no_sensitive_fields_or_cache(self):
        self.login()
        response = self.client.get('/api/corporate/me')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertNotIn('senha', response.get_data(as_text=True))
        self.assertNotIn('base_url', self.client.get('/api/corporate/systems').get_data(as_text=True))

    def test_origin_validator(self):
        for url in ('javascript:alert(1)', 'data:text/plain,a', 'file:///etc/passwd',
                    'https://user:pass@legit.example',
                    'https://legit.example/path', 'http://legit.example',
                    'https://legit.example?next=evil', '//legit.example'):
            self.assertIsNone(safe_system_url(url), url)
        self.assertEqual(safe_system_url('https://legit.example/'), 'https://legit.example')


if __name__ == '__main__': unittest.main()
