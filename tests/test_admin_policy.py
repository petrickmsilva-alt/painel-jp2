"""Single policy used by legacy JP2 and corporate management."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('FLASK_SECRET_KEY', 'local-tests-not-a-production-secret')
from app import app, usuario_login_e_admin, usuario_atual_e_admin
from corporate import is_admin
from identity_policy import is_administrator


class Cursor:
    def __init__(self, user): self.user = user
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, sql, params): self.username = params[0]
    def fetchone(self):
        return self.user if self.user and self.user['usuario'] == self.username else None


class Connection:
    def __init__(self, user): self.user = user
    def cursor(self): return Cursor(self.user)
    def close(self): pass


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.user = {'id': 41, 'usuario': 'configured', 'perfil': 'socio'}
        self.env = patch.dict(os.environ, {'ADMIN_USERS': 'configured'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def check_all(self, expected):
        self.assertEqual(is_administrator(self.user), expected)
        self.assertEqual(is_admin(self.user), expected)
        self.assertEqual(usuario_login_e_admin(self.user), expected)
        with app.test_request_context('/'):
            from flask import session
            session['usuario_logado'] = self.user['usuario'] if self.user else 'deleted'
            session['perfil_usuario'] = 'admin'  # old cookie cannot override DB
            with patch('app.garantir_coluna_perfil_usuarios'), patch('app.get_db_connection', return_value=Connection(self.user)):
                self.assertEqual(usuario_atual_e_admin(), expected)

    def test_configured_admin_requires_existing_db_user(self):
        self.check_all(True)
        self.user = None
        self.check_all(False)

    def test_profile_admin(self):
        self.user = {'id': 42, 'usuario': 'profile', 'perfil': 'admin'}
        self.check_all(True)

    def test_normal_user_and_stale_role(self):
        self.user = {'id': 43, 'usuario': 'normal', 'perfil': 'socio'}
        self.check_all(False)
        self.user['perfil'] = 'admin'
        self.check_all(True)
        self.user['perfil'] = 'leitura'
        self.check_all(False)

    def test_login_rotates_company_context_and_pending_mfa(self):
        from flask import session
        from app import finalizar_login_usuario, iniciar_fluxo_2fa
        with app.test_request_context('/'):
            session['corporate_empresa_id'] = 200
            session['usuario_logado'] = 'other'
            iniciar_fluxo_2fa({'usuario': 'configured', 'perfil': 'socio'})
            self.assertNotIn('corporate_empresa_id', session)
            session['corporate_empresa_id'] = 200
            with patch('app.registrar_log'), patch('app.limpar_falhas_login'):
                finalizar_login_usuario(self.user)
            self.assertEqual(session['usuario_logado'], 'configured')
            self.assertNotIn('corporate_empresa_id', session)
            self.assertNotIn('2fa_pending_user', session)

    def test_cookie_claim_and_missing_identity_cannot_escalate(self):
        self.user = {'id': 44, 'usuario': 'normal', 'perfil': 'admin'}
        self.check_all(True)
        self.user = {'id': 44, 'usuario': 'normal', 'perfil': 'leitura'}
        self.check_all(False)
        self.assertFalse(is_administrator({'usuario': 'configured', 'perfil': 'admin'}))


if __name__ == '__main__':
    unittest.main()
