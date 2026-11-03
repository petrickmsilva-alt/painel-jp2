"""Isolated unit tests for the opt-in legacy-route gate. No real database."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('FLASK_SECRET_KEY', 'local-tests-not-a-production-secret')
os.environ.setdefault('FLASK_COOKIE_SECURE', 'false')
from app import app
import corporate_enforcement as gate


class Cursor:
    def __init__(self, state):
        self.state = state
        self.one = None
        self.many = []

    def __enter__(self): return self
    def __exit__(self, *args): pass

    def execute(self, sql, params=()):
        self.one = None
        self.many = []
        if 'FROM usuarios WHERE usuario' in sql:
            self.one = self.state['user']
        elif 'FROM corporate_memberships m JOIN empresas' in sql:
            self.many = self.state['members']
        elif 'INSERT INTO corporate_audit' in sql:
            self.state['audits'].append(params)
        else:
            raise AssertionError('Unexpected query: ' + sql)

    def fetchone(self): return self.one
    def fetchall(self): return self.many


class Connection:
    def __init__(self, state):
        self.state = state
        self.closed = False

    def cursor(self): return Cursor(self.state)
    def close(self): self.closed = True


class EnforcementTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        os.environ.pop('JP2_REVOCABLE_SESSIONS', None)
        self.log = patch('logging.exception')
        self.log.start()
        self.addCleanup(self.log.stop)
        self.state = {
            'user': {'id': 1, 'usuario': 'alice', 'nome_exibicao': 'Alice', 'perfil': 'socio'},
            'members': [{'id': 10, 'user_id': 1, 'empresa_id': 100, 'role': 'socio',
                         'company_name': 'Empresa A'}],
            'audits': [],
        }
        self.conns = []

    def db(self):
        conn = Connection(self.state)
        self.conns.append(conn)
        return conn

    def client(self, user='alice', company=100):
        client = app.test_client()
        with client.session_transaction() as sess:
            if user:
                sess['usuario_logado'] = user
            if company is not None:
                sess['corporate_empresa_id'] = company
            sess['_csrf_token'] = 'test-csrf'
        return client

    def gate_on(self):
        return patch.dict(os.environ, {'JP2_ENFORCE_CORPORATE_CONTEXT': '1'})

    def test_flag_desligada_nao_consulta_o_banco(self):
        with patch.object(gate, 'get_db_connection', side_effect=AssertionError('banco consultado')):
            resposta = self.client().get('/carteira-investimentos')
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self.state['audits'], [])

    def test_usuario_inexistente_no_banco_e_negado_e_auditado(self):
        self.state['user'] = None
        with self.gate_on(), patch.object(gate, 'get_db_connection', side_effect=self.db):
            resposta = self.client().get('/carteira-investimentos')
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(len(self.state['audits']), 1)
        self.assertEqual(self.state['audits'][0][:2], ('LEGACY_CONTEXT_DENIED', None))
        self.assertEqual(self.state['audits'][0][4], 'denied')
        self.assertTrue(all(conn.closed for conn in self.conns))

    def test_sem_membership_ativa_e_negado(self):
        self.state['members'] = []
        with self.gate_on(), patch.object(gate, 'get_db_connection', side_effect=self.db):
            resposta = self.client().get('/carteira-investimentos')
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(self.state['audits'][0][1], 1)

    def test_contexto_valido_e_permitido(self):
        with self.gate_on(), patch.object(gate, 'get_db_connection', side_effect=self.db):
            resposta = self.client().get('/carteira-investimentos')
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self.state['audits'], [])

    def test_empresa_id_divergente_e_negado(self):
        with self.gate_on(), patch.object(gate, 'get_db_connection', side_effect=self.db):
            resposta = self.client().get('/carteira-investimentos?empresa_id=200')
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(self.state['audits'][0][2], 100)

    def test_empresa_id_invalido_e_negado(self):
        with self.gate_on(), patch.object(gate, 'get_db_connection', side_effect=self.db):
            resposta = self.client().get('/carteira-investimentos?empresa_id=abc')
        self.assertEqual(resposta.status_code, 403)

    def test_empresa_id_coerente_em_json_e_permitido(self):
        with self.gate_on(), patch.object(gate, 'get_db_connection', side_effect=self.db):
            resposta = self.client().get('/carteira-investimentos', json={'empresa_id': 100})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self.state['audits'], [])

    def test_rota_de_efeito_global_e_bloqueada(self):
        with self.gate_on(), patch.object(gate, 'get_db_connection', side_effect=self.db):
            resposta = self.client().get('/api/empresas')
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(self.state['audits'][0][4], 'denied')

    def test_falha_de_banco_falha_fechada(self):
        with self.gate_on(), patch.object(gate, 'get_db_connection', side_effect=RuntimeError('db off')):
            resposta = self.client().get('/carteira-investimentos')
        self.assertEqual(resposta.status_code, 403)
        corpo = resposta.get_data(as_text=True)
        self.assertNotIn('db off', corpo)
        self.assertNotIn('SELECT', corpo)
        self.assertNotIn('Traceback', corpo)

    def test_rotas_isentas_nao_consultam_o_banco(self):
        with self.gate_on(), patch.object(gate, 'get_db_connection',
                                          side_effect=AssertionError('banco consultado')):
            for caminho in ('/login', '/manifest.json', '/2fa/verificar'):
                resposta = app.test_client().get(caminho)
                self.assertNotEqual(resposta.status_code, 403, caminho)
                resposta.close()

    def test_rotas_corporativas_sao_isentas_do_gate(self):
        with self.gate_on(), patch.object(gate, 'get_db_connection',
                                          side_effect=AssertionError('banco consultado')):
            with app.test_request_context('/api/corporate/me'):
                self.assertIsNone(gate.avaliar_contexto())
            with app.test_request_context('/sistemas'):
                self.assertIsNone(gate.avaliar_contexto())
