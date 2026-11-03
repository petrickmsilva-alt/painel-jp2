"""Opt-in corporate context gate for legacy Flask routes (Fase 2).

This is an ACCESS GATE, not data-level tenant isolation and not an OIDC
provider. Legacy modules still query their own tables without a membership
filter; see docs/JP2-FASE2-GATES-AND-ENFORCEMENT.md for the explicit limits.

Disabled by default. Enabling it without first reviewing memberships and
grants can block legitimate users, exactly as warned in the Fase 1 route
matrix. Fail-closed: a database error denies the request.
"""
import logging
import os

from flask import abort, request, session
from werkzeug.exceptions import HTTPException

from corporate import audit, current_user, selected_membership
from database import get_db_connection

FLAG = 'JP2_ENFORCE_CORPORATE_CONTEXT'
TRUTHY = ('1', 'true', 'yes', 'on')
AUSENTE = object()
INVALIDO = object()

# Authentication, static assets and the corporate control plane are exempt:
# the latter already reloads identity and validates membership on its own.
EXEMPT_PATHS = frozenset(('/manifest.json', '/OneSignalSDKWorker.js'))
EXEMPT_PREFIXES = ('/login', '/logout', '/2fa', '/static/')
EXEMPT_ENDPOINT_PREFIX = 'corporate.'

# Routes whose effects are global (no membership filter in the legacy SQL).
# While the gate is on they are denied instead of being presented as scoped.
BLOCKED_PREFIXES = (
    '/api/empresas',
    '/api/adicionar-empresa',
    '/api/excluir-empresa',
    '/api/preview-importacao-investimentos',
    '/api/importar-investimentos-excel',
    '/api/limpar-investimentos',
    '/api/excluir-investimentos-lote',
)


def enabled():
    return os.environ.get(FLAG, '0').strip().lower() in TRUTHY


def is_exempt():
    path = request.path
    endpoint = request.endpoint or ''
    return (path in EXEMPT_PATHS or path.startswith(EXEMPT_PREFIXES)
            or endpoint in ('', 'static') or endpoint.startswith(EXEMPT_ENDPOINT_PREFIX))


def empresa_id_enviada():
    """Client-supplied company id: AUSENTE, INVALIDO or a positive int."""
    valor = request.args.get('empresa_id')
    if valor is None:
        valor = request.form.get('empresa_id')
    if valor is None and request.is_json:
        dados = request.get_json(silent=True)
        if isinstance(dados, dict):
            valor = dados.get('empresa_id')
    if valor is None:
        return AUSENTE
    if isinstance(valor, bool) or not isinstance(valor, (int, str)):
        return INVALIDO
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return INVALIDO
    return numero if numero > 0 else INVALIDO


def _negar(cur, user_id, company_id, motivo):
    logging.info('Gate corporativo negou acesso: %s', motivo)
    try:
        audit(cur, 'LEGACY_CONTEXT_DENIED', user_id, company_id, result='denied')
    except Exception:
        # A broken audit table must never turn a denial into an allowance.
        logging.exception('Falha ao auditar negativa do gate corporativo')
    # Deliberately opaque: no reason, ids, SQL or stack trace reach the client.
    abort(403)


def avaliar_contexto():
    """Return None to allow, raise HTTPException to deny. Called before every request."""
    if not enabled() or is_exempt():
        return None
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            user = current_user(cur)
            if not user:
                _negar(cur, None, None, 'identidade nao confirmada no banco')
            member = selected_membership(cur, user['id'])
            if not member:
                contexto = session.get('corporate_empresa_id')
                _negar(cur, user['id'], contexto if type(contexto) is int else None,
                       'sem membership ativa no contexto selecionado')
            if request.path.startswith(BLOCKED_PREFIXES):
                _negar(cur, user['id'], member['empresa_id'], 'rota de efeito global bloqueada')
            valor = empresa_id_enviada()
            if valor is INVALIDO or (valor is not AUSENTE and valor != member['empresa_id']):
                _negar(cur, user['id'], member['empresa_id'], 'empresa_id divergente do contexto')
            return None
    except HTTPException:
        raise
    except Exception:
        logging.exception('Gate corporativo indisponivel; negando por padrao')
        abort(403)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                logging.exception('Falha ao fechar conexao do gate corporativo')


def install(app):
    @app.before_request
    def exigir_contexto_corporativo():
        return avaliar_contexto()
