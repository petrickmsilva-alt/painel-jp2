"""Opt-in server-side session foundation for JP2 (Fase 2).

An internal opaque handle is kept in the signed Flask cookie and checked
against a MySQL row on every authenticated request, so an administrator can
revoke a session that is still inside its cookie lifetime.

It is NOT a federated identity artefact: no OIDC/OAuth endpoints, no signed
claims, no bearer credential, nothing accepted by ERP or Commerce. It is a
local session row only. Disabled by default; requires the manual migration
migrations/20261104_revocable_sessions.sql and the Fase 1 tables.
"""
import hashlib
import logging
import os
import secrets

from flask import jsonify, redirect, request, session, url_for

from database import get_db_connection

FLAG = 'JP2_REVOCABLE_SESSIONS'
COOKIE_KEY = 'jp2_sid'
TRUTHY = ('1', 'true', 'yes', 'on')
TTL_HORAS = 8
EXEMPT_PATHS = frozenset(('/manifest.json', '/OneSignalSDKWorker.js'))
EXEMPT_PREFIXES = ('/login', '/logout', '/2fa', '/static/')
REASONS = ('logout', 'admin', 'password_change', 'membership_revoked', 'expired')


def enabled():
    return os.environ.get(FLAG, '0').strip().lower() in TRUTHY


def _hash(sid):
    return hashlib.sha256(sid.encode('utf-8')).hexdigest()


def issue(conn, user_id, ttl_hours=TTL_HORAS):
    """Create a session row; only the SHA-256 digest of the handle is stored."""
    sid = secrets.token_urlsafe(32)
    with conn.cursor() as cur:
        cur.execute('''INSERT INTO jp2_sessions (sid_hash, user_id, expires_at)
                       VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL %s HOUR))''',
                    (_hash(sid), int(user_id), int(ttl_hours)))
    return sid


def validate(conn, sid):
    """Return the live row, or None when absent, revoked or expired."""
    if not isinstance(sid, str) or not sid or len(sid) > 256:
        return None
    with conn.cursor() as cur:
        cur.execute('''SELECT sid_hash, user_id, expires_at, revoked_at
                       FROM jp2_sessions
                       WHERE sid_hash=%s AND revoked_at IS NULL AND expires_at > NOW()''',
                    (_hash(sid),))
        return cur.fetchone()


def revoke(conn, sid, reason='logout'):
    if not isinstance(sid, str) or not sid:
        return 0
    with conn.cursor() as cur:
        cur.execute('''UPDATE jp2_sessions SET revoked_at=NOW(), revoke_reason=%s
                       WHERE sid_hash=%s AND revoked_at IS NULL''',
                    (reason if reason in REASONS else 'admin', _hash(sid)))
        return cur.rowcount


def revoke_user(conn, user_id, reason='admin'):
    """Administrative revocation: invalidates every live cookie of a user."""
    with conn.cursor() as cur:
        cur.execute('''UPDATE jp2_sessions SET revoked_at=NOW(), revoke_reason=%s
                       WHERE user_id=%s AND revoked_at IS NULL''',
                    (reason if reason in REASONS else 'admin', int(user_id)))
        return cur.rowcount


def registrar_sessao_apos_login(user, sess):
    """Called by finalizar_login_usuario. No-op unless the flag is on."""
    if not enabled():
        return
    conn = get_db_connection()
    try:
        sid = issue(conn, user['id'])
    finally:
        conn.close()
    sess[COOKIE_KEY] = sid


def revogar_sessao_atual(sess):
    """Called by logout. Best effort: the browser cookie is cleared regardless."""
    if not enabled():
        return
    sid = sess.get(COOKIE_KEY)
    if not isinstance(sid, str) or not sid:
        return
    try:
        conn = get_db_connection()
        try:
            revoke(conn, sid, 'logout')
        finally:
            conn.close()
    except Exception:
        logging.exception('Falha ao revogar sessao no logout')


def _encerrar():
    session.clear()
    if request.path.startswith('/api/'):
        return jsonify({'error': 'sessao invalida ou revogada'}), 401
    return redirect(url_for('tela_login'))


def avaliar_sessao():
    """Return None to allow, or a response that ends the session. Fail-closed."""
    if not enabled():
        return None
    if request.path in EXEMPT_PATHS or request.path.startswith(EXEMPT_PREFIXES) or not request.endpoint:
        return None
    if 'usuario_logado' not in session:
        return None
    sid = session.get(COOKIE_KEY)
    if not isinstance(sid, str) or not sid:
        return _encerrar()
    try:
        conn = get_db_connection()
        try:
            row = validate(conn, sid)
        finally:
            conn.close()
    except Exception:
        logging.exception('Validacao de sessao falhou; negando por padrao')
        return _encerrar()
    if row is None:
        return _encerrar()
    return None


def install(app):
    @app.before_request
    def validar_sessao_revogavel():
        return avaliar_sessao()
