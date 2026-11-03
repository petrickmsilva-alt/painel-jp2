"""Isolated unit tests for the opt-in revocable-session foundation. No real DB."""
import hashlib
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

os.environ.setdefault('FLASK_SECRET_KEY', 'local-tests-not-a-production-secret')
os.environ.setdefault('FLASK_COOKIE_SECURE', 'false')
from app import app
import revocable_sessions as rs


class FakeSessions:
    def __init__(self):
        self.rows = {}
        self.last_hash = None
        self.one = None
        self.rowcount = 0

    def __enter__(self): return self
    def __exit__(self, *args): pass

    def execute(self, sql, params=()):
        self.one = None
        self.rowcount = 0
        if sql.startswith('INSERT INTO jp2_sessions'):
            digest, user_id, ttl = params
            self.rows[digest] = {'sid_hash': digest, 'user_id': user_id,
                                 'expires_at': datetime.now() + timedelta(hours=ttl),
                                 'revoked_at': None}
            self.last_hash = digest
        elif sql.startswith('SELECT sid_hash'):
            row = self.rows.get(params[0])
            if row and row['revoked_at'] is None and row['expires_at'] > datetime.now():
                self.one = row
        elif sql.startswith('UPDATE jp2_sessions') and 'WHERE sid_hash' in sql:
            reason, digest = params
            row = self.rows.get(digest)
            if row and row['revoked_at'] is None:
                row['revoked_at'] = datetime.now()
                row['revoke_reason'] = reason
                self.rowcount = 1
        elif sql.startswith('UPDATE jp2_sessions') and 'WHERE user_id' in sql:
            reason, user_id = params
            for row in self.rows.values():
                if row['user_id'] == user_id and row['revoked_at'] is None:
                    row['revoked_at'] = datetime.now()
                    row['revoke_reason'] = reason
                    self.rowcount += 1
        else:
            raise AssertionError('Unexpected query: ' + sql)

    def fetchone(self): return self.one


class Connection:
    def __init__(self, state): self.state = state
    def cursor(self): return self.state
    def close(self): pass


class SessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        os.environ.pop('JP2_ENFORCE_CORPORATE_CONTEXT', None)
        os.environ.pop('JP2_REVOCABLE_SESSIONS', None)
        self.log = patch('logging.exception')
        self.log.start()
        self.addCleanup(self.log.stop)
        self.store = FakeSessions()
        self.conn = Connection(self.store)

    def on(self):
        return patch.dict(os.environ, {'JP2_REVOCABLE_SESSIONS': '1'})

    def client(self, sid=None):
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['usuario_logado'] = 'alice'
            sess['_csrf_token'] = 'test-csrf'
            if sid is not None:
                sess[rs.COOKIE_KEY] = sid
        return client

    def test_flags_desligadas_por_padrao(self):
        self.assertFalse(rs.enabled())
        self.assertFalse(__import__('corporate_enforcement').enabled())

    def test_issue_guarda_apenas_o_digest(self):
        sid = rs.issue(self.conn, 1)
        self.assertEqual(len(sid) >= 32, True)
        self.assertIn(hashlib.sha256(sid.encode()).hexdigest(), self.store.rows)
        self.assertNotIn(sid, self.store.rows)
        self.assertEqual(self.store.rows[self.store.last_hash]['user_id'], 1)

    def test_validate_revoke_expiracao_e_revogacao_por_usuario(self):
        sid = rs.issue(self.conn, 1)
        self.assertEqual(rs.validate(self.conn, sid)['user_id'], 1)
        self.assertEqual(rs.revoke(self.conn, sid, 'admin'), 1)
        self.assertIsNone(rs.validate(self.conn, sid))
        self.assertEqual(rs.revoke(self.conn, sid, 'admin'), 0)

        expirado = rs.issue(self.conn, 2)
        self.store.rows[hashlib.sha256(expirado.encode()).hexdigest()]['expires_at'] = (
            datetime.now() - timedelta(minutes=1))
        self.assertIsNone(rs.validate(self.conn, expirado))

        vivo = rs.issue(self.conn, 2)
        # A linha expirada (ainda nao revogada) tambem entra na revogacao por usuario.
        self.assertGreaterEqual(rs.revoke_user(self.conn, 2, 'membership_revoked'), 1)
        self.assertIsNone(rs.validate(self.conn, vivo))

    def test_validate_rejeita_handle_invalido(self):
        for valor in (None, '', 123, 'x' * 300):
            self.assertIsNone(rs.validate(self.conn, valor))

    def test_login_sem_flag_nao_abre_banco(self):
        sess = {}
        with patch.object(rs, 'get_db_connection', side_effect=AssertionError('banco consultado')):
            rs.registrar_sessao_apos_login({'id': 1}, sess)
        self.assertEqual(sess, {})

    def test_login_com_flag_registra_linha(self):
        sess = {}
        with self.on(), patch.object(rs, 'get_db_connection', return_value=self.conn):
            rs.registrar_sessao_apos_login({'id': 1}, sess)
        self.assertIn(rs.COOKIE_KEY, sess)
        self.assertEqual(rs.validate(self.conn, sess[rs.COOKIE_KEY])['user_id'], 1)

    def test_logout_sem_flag_nao_abre_banco(self):
        with patch.object(rs, 'get_db_connection', side_effect=AssertionError('banco consultado')):
            rs.revogar_sessao_atual({rs.COOKIE_KEY: 'qualquer'})

    def test_logout_com_flag_revoga(self):
        sid = rs.issue(self.conn, 1)
        with self.on(), patch.object(rs, 'get_db_connection', return_value=self.conn):
            rs.revogar_sessao_atual({rs.COOKIE_KEY: sid})
        self.assertIsNone(rs.validate(self.conn, sid))

    def test_hook_sem_handle_encerra_sessao(self):
        with self.on(), patch.object(rs, 'get_db_connection', return_value=self.conn):
            resposta = self.client().get('/carteira-investimentos')
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/login', resposta.headers['Location'])

    def test_hook_sem_handle_responde_401_em_api(self):
        with self.on(), patch.object(rs, 'get_db_connection', return_value=self.conn):
            resposta = self.client().get('/api/performance-status')
        self.assertEqual(resposta.status_code, 401)

    def test_hook_com_sessao_valida_permite(self):
        sid = rs.issue(self.conn, 1)
        with self.on(), patch.object(rs, 'get_db_connection', return_value=self.conn):
            resposta = self.client(sid).get('/carteira-investimentos')
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/carteira', resposta.headers['Location'])

    def test_hook_com_sessao_revogada_encerra(self):
        sid = rs.issue(self.conn, 1)
        rs.revoke_user(self.conn, 1, 'admin')
        with self.on(), patch.object(rs, 'get_db_connection', return_value=self.conn):
            resposta = self.client(sid).get('/carteira-investimentos')
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/login', resposta.headers['Location'])

    def test_falha_de_banco_no_hook_falha_fechada(self):
        with self.on(), patch.object(rs, 'get_db_connection', side_effect=RuntimeError('db off')):
            resposta = self.client('handle-qualquer').get('/carteira-investimentos')
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/login', resposta.headers['Location'])
