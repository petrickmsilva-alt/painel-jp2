"""Runs the same read-only contract gate used by CI as a unit test."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('FLASK_SECRET_KEY', 'local-tests-not-a-production-secret')
os.environ.setdefault('FLASK_COOKIE_SECURE', 'false')
sys.path.insert(0, str(ROOT / 'scripts'))
import check_contract  # noqa: E402


class ContractTests(unittest.TestCase):
    def test_contrato_da_fase2_sem_violacoes(self):
        self.assertEqual(check_contract.run_checks(), [])

    def test_nenhuma_rota_de_federacao_registrada(self):
        from app import app
        proibidos = ('/oauth', '/jwks', '/userinfo', '.well-known', 'openid-configuration')
        rotas = [r.rule for r in app.url_map.iter_rules()]
        self.assertEqual([r for r in rotas if any(p in r.lower() for p in proibidos)], [])
