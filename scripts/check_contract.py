"""Fase 2 CI contract gate. Read-only: no database, no network, no file writes.

Fails the build if the Fase 2 contract is broken (OIDC endpoints appear,
flags stop defaulting to off, runtime DDL/migrations appear, external
access creeps into the new modules, the documented route inventory drifts,
or the honest-status document stops declaring the known limits).
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('FLASK_SECRET_KEY', 'contract-check-not-a-production-secret')
os.environ.setdefault('FLASK_COOKIE_SECURE', 'false')
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402
import corporate_enforcement as enforcement  # noqa: E402
import revocable_sessions as sessions  # noqa: E402

NEW_MODULES = ('corporate_enforcement.py', 'revocable_sessions.py')
FEDERATION_MARKERS = re.compile(
    r'(?i)\b(jwt|id_token|access_token|refresh_token|client_secret|code_verifier|'
    r'authorization_code|openid-configuration|jwks)\b|/\.well-known')
EXTERNAL_ACCESS = re.compile(r'(?i)https?://|urllib\.request|import\s+requests|import\s+httpx')
RUNTIME_DDL = re.compile(r'(?i)\b(CREATE|ALTER|DROP)\s+TABLE\b')
OIDC_ROUTE_MARKERS = ('/oauth', '/jwks', '/userinfo', '.well-known', 'openid-configuration')


def _text(path):
    return (ROOT / path).read_text(encoding='utf-8')


def run_checks():
    """Return a list of contract violations; empty means the gate passed."""
    failures = []
    rules = sorted(r.rule for r in app.url_map.iter_rules())

    bad_routes = [r for r in rules if any(marker in r.lower() for marker in OIDC_ROUTE_MARKERS)]
    if bad_routes:
        failures.append('OIDC_IMPLEMENTED=NO violado: rotas de federacao registradas: ' + ', '.join(bad_routes))
    oidc_files = [p.name for p in ROOT.glob('oidc*.py')] + [p.name for p in ROOT.glob('oauth*.py')]
    if oidc_files:
        failures.append('Modulos de provedor OIDC nao devem existir nesta fase: ' + ', '.join(oidc_files))

    matrix = _text('docs/JP2-LEGACY-ROUTE-MATRIX.md')
    match = re.search(r'Total:\s*(\d+)\s*rotas', matrix)
    if not match or int(match.group(1)) != len(rules):
        failures.append('Inventario de rotas divergente: doc=%s, url_map=%s' %
                        (match.group(1) if match else '?', len(rules)))

    saved = {name: os.environ.get(name) for name in (enforcement.FLAG, sessions.FLAG)}
    try:
        for name in saved:
            os.environ.pop(name, None)
        if enforcement.enabled() or sessions.enabled():
            failures.append('Flags da Fase 2 nao estao desligadas por padrao')
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    for name in NEW_MODULES:
        source = _text(name)
        if FEDERATION_MARKERS.search(source):
            failures.append('%s contem artefato de federacao/token' % name)
        if EXTERNAL_ACCESS.search(source):
            failures.append('%s contem URL externa ou cliente HTTP (ERP/Commerce)' % name)
        if RUNTIME_DDL.search(source):
            failures.append('%s executa DDL ou migration em tempo de request' % name)

    migration = _text('migrations/20261104_revocable_sessions.sql')
    statements = []
    for statement in migration.split(';'):
        clean = '\n'.join(line for line in statement.splitlines()
                          if not line.strip().startswith('--')).strip()
        if clean:
            statements.append(clean)
    if len(statements) != 1 or not statements[0].upper().startswith('CREATE TABLE IF NOT EXISTS JP2_SESSIONS'):
        failures.append('Migration da Fase 2 nao cria jp2_sessions de forma idempotente')
    if any(re.match(r'(?i)^(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT)\b', s) for s in statements):
        failures.append('Migration da Fase 2 contem operacao de dados/DDL destrutiva')

    seeds = _text('migrations/20261103_corporate_authority.sql')
    for slug in ('brobond-erp', 'brobond-commerce'):
        line = next((ln for ln in seeds.splitlines() if slug in ln), '')
        if 'inactive' not in line:
            failures.append('Seed %s nao esta inativo no catalogo' % slug)

    doc = _text('docs/JP2-FASE2-GATES-AND-ENFORCEMENT.md')
    for marker in ('OIDC_IMPLEMENTED = NO',
                   'ENFORCEMENT_PADRAO = DESLIGADO',
                   'ISOLAMENTO_GLOBAL_DE_DADOS = NAO COMPROVADO',
                   'MYSQL_DE_HOMOLOGACAO = NAO EXECUTADO'):
        if marker not in doc:
            failures.append('Documento de status nao declara: ' + marker)
    return failures


def main():
    failures = run_checks()
    print('Rotas registradas: %d | Flags: desligadas por padrao | OIDC_IMPLEMENTED=NO'
          % len(list(app.url_map.iter_rules())))
    if failures:
        for item in failures:
            print('CONTRACT FAIL: ' + item)
        return 1
    print('CONTRACT PASS: nenhuma violacao do contrato da Fase 2')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
