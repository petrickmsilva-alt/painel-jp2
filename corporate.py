"""Corporate control plane for the existing Flask/MySQL panel; NOT an OIDC provider."""
from urllib.parse import urlsplit
from uuid import uuid4

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from database import get_db_connection

bp_corporate = Blueprint('corporate', __name__)
ROLES = ('admin', 'socio', 'leitura')  # Existing JP2 nomenclature; corporate role is per company.
ENVIRONMENTS = ('DEVELOPMENT', 'STAGING', 'PRODUCTION')


def safe_system_url(value):
    """Only a registered absolute HTTPS origin (no userinfo, path, query or fragment)."""
    if not value:
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or
                parsed.password or parsed.path not in ('', '/') or parsed.query or
                parsed.fragment or value != value.strip() or any(c.isspace() for c in value)):
            return None
        if parsed.port is not None and parsed.port != 443:
            return None
        return parsed.geturl().rstrip('/')
    except ValueError:
        return None


def current_user(cur):
    username = session.get('usuario_logado')
    if not username:
        return None
    cur.execute('SELECT id, usuario, nome_exibicao, perfil FROM usuarios WHERE usuario = %s', (username,))
    return cur.fetchone()


def memberships(cur, user_id):
    cur.execute('''SELECT m.id, m.empresa_id, m.role, e.nome AS company_name
                   FROM corporate_memberships m JOIN empresas e ON e.id = m.empresa_id
                   WHERE m.user_id = %s AND m.status = 'active' ORDER BY e.nome''', (user_id,))
    return cur.fetchall()


def selected_membership(cur, user_id):
    company_id = session.get('corporate_empresa_id')
    # No implicit tenant selection. Company context must be explicitly selected and revalidated.
    if type(company_id) is not int:
        return None
    return next((m for m in memberships(cur, user_id) if m['empresa_id'] == company_id), None)


def allowed_systems(cur, membership_id):
    cur.execute('''SELECT s.id, s.slug, s.name, s.description, s.environment
                   FROM corporate_systems s JOIN corporate_system_access a ON a.system_id = s.id
                   WHERE a.membership_id = %s AND s.status = 'active' ORDER BY s.name''', (membership_id,))
    return cur.fetchall()


def audit(cur, action, user_id, company_id=None, system_id=None, result='allowed'):
    cur.execute('''INSERT INTO corporate_audit (action,user_id,empresa_id,system_id,result,correlation_id,ip,user_agent)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
                (action, user_id, company_id, system_id, result, uuid4().hex,
                 request.remote_addr, request.user_agent.string[:255]))


def is_admin(user):
    # Recheck DB; a stale cookie cannot retain administrative privileges after role change.
    return bool(user and user['perfil'] == 'admin')


@bp_corporate.route('/api/corporate/me')
def me():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            user = current_user(cur)
            if not user:
                return jsonify({'error': 'unauthorized'}), 401
            member = selected_membership(cur, user['id'])
            own = memberships(cur, user['id'])
            systems = allowed_systems(cur, member['id']) if member else []
            return jsonify({'user': {k: user[k] for k in ('id', 'usuario', 'nome_exibicao')},
                            'company': {'id': member['empresa_id'], 'name': member['company_name']} if member else None,
                            'memberships': [{'company_id': m['empresa_id'], 'company_name': m['company_name'], 'role': m['role']} for m in own],
                            'roles': [member['role']] if member else [],
                            'systems': systems})


@bp_corporate.route('/api/corporate/systems')
def systems():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            user = current_user(cur)
            if not user:
                return jsonify({'error': 'unauthorized'}), 401
            member = selected_membership(cur, user['id'])
            result = allowed_systems(cur, member['id']) if member else []
            audit(cur, 'SYSTEM_ACCESS', user['id'], member['empresa_id'] if member else None,
                  result='allowed' if member else 'denied')
            return jsonify({'systems': result})


@bp_corporate.route('/sistemas')
def index():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            user = current_user(cur)
            if not user:
                return redirect(url_for('tela_login'))
            own = memberships(cur, user['id'])
            member = selected_membership(cur, user['id'])
            systems = allowed_systems(cur, member['id']) if member else []
            from app import obter_csrf_token
            return render_template('corporate_systems.html', memberships=own, member=member,
                                   systems=systems, admin=is_admin(user), csrf=obter_csrf_token())


@bp_corporate.route('/sistemas/contexto', methods=['POST'])
def set_context():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            user = current_user(cur)
            if not user:
                abort(401)
            try:
                company_id = int(request.form.get('empresa_id', ''))
            except ValueError:
                abort(400)
            if not any(m['empresa_id'] == company_id for m in memberships(cur, user['id'])):
                audit(cur, 'COMPANY_CHANGED', user['id'], company_id, result='denied')
                abort(403)
            session['corporate_empresa_id'] = company_id
            audit(cur, 'COMPANY_CHANGED', user['id'], company_id)
            return redirect(url_for('corporate.index'))


@bp_corporate.route('/sistemas/<slug>')
def detail(slug):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            user = current_user(cur)
            if not user:
                return redirect(url_for('tela_login'))
            member = selected_membership(cur, user['id'])
            system = next((s for s in allowed_systems(cur, member['id']) if s['slug'] == slug), None) if member else None
            if not system:
                audit(cur, 'SYSTEM_ACCESS_DENIED', user['id'], member['empresa_id'] if member else None, result='denied')
                abort(404)  # Do not disclose system existence to unentitled users.
            audit(cur, 'SYSTEM_ACCESS', user['id'], member['empresa_id'], system['id'])
            return render_template('corporate_detail.html', system=system, member=member)


@bp_corporate.route('/admin/acessos', methods=['GET', 'POST'])
def manage():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            actor = current_user(cur)
            if not actor:
                abort(401)
            if not is_admin(actor):
                abort(403)
            if request.method == 'POST':
                try:
                    user_id = int(request.form.get('user_id', ''))
                    company_id = int(request.form.get('empresa_id', ''))
                except ValueError:
                    abort(400)
                cur.execute('SELECT id FROM usuarios WHERE id = %s', (user_id,))
                if not cur.fetchone():
                    abort(400)
                cur.execute('SELECT id FROM empresas WHERE id = %s', (company_id,))
                if not cur.fetchone():
                    abort(400)
                action = request.form.get('action')
                if action == 'membership':
                    role = request.form.get('role')
                    status = request.form.get('status')
                    if role not in ROLES or status not in ('active', 'revoked'):
                        abort(400)
                    cur.execute('''INSERT INTO corporate_memberships (user_id, empresa_id, role, status)
                                   VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE role=VALUES(role), status=VALUES(status)''',
                                (user_id, company_id, role, status))
                    audit(cur, 'MEMBERSHIP_CHANGED', actor['id'], company_id)
                elif action == 'access':
                    slug = request.form.get('slug')
                    grant = request.form.get('grant')
                    if grant not in ('yes', 'no'):
                        abort(400)
                    cur.execute('SELECT id FROM corporate_systems WHERE slug = %s', (slug,))
                    system = cur.fetchone()
                    cur.execute('''SELECT id, status FROM corporate_memberships
                                   WHERE user_id = %s AND empresa_id = %s''', (user_id, company_id))
                    member = cur.fetchone()
                    if not member or member['status'] != 'active' or not system:
                        abort(400)
                    if grant == 'yes':
                        cur.execute('INSERT IGNORE INTO corporate_system_access (membership_id, system_id) VALUES (%s,%s)', (member['id'], system['id']))
                    else:
                        cur.execute('DELETE FROM corporate_system_access WHERE membership_id = %s AND system_id = %s', (member['id'], system['id']))
                    audit(cur, 'SYSTEM_ACCESS_GRANTED' if grant == 'yes' else 'SYSTEM_ACCESS_REVOKED', actor['id'], company_id, system['id'])
                elif action == 'system':
                    slug = request.form.get('slug')
                    status = request.form.get('status')
                    environment = request.form.get('environment')
                    base_url = request.form.get('base_url', '').strip()
                    if status not in ('active', 'inactive') or environment not in ENVIRONMENTS or (base_url and not safe_system_url(base_url)):
                        abort(400)
                    cur.execute('UPDATE corporate_systems SET status=%s, environment=%s, base_url=%s WHERE slug=%s',
                                (status, environment, safe_system_url(base_url), slug))
                    if cur.rowcount == 0:
                        # MySQL reports zero for an unchanged row; verify its existence independently.
                        cur.execute('SELECT id FROM corporate_systems WHERE slug=%s', (slug,))
                        if not cur.fetchone():
                            abort(400)
                    audit(cur, 'SYSTEM_CHANGED', actor['id'])
                else:
                    abort(400)
                return redirect(url_for('corporate.manage'))
            cur.execute('SELECT id, usuario FROM usuarios ORDER BY usuario')
            users = cur.fetchall()
            cur.execute('SELECT id, nome FROM empresas ORDER BY nome')
            companies = cur.fetchall()
            cur.execute('SELECT slug, name, status, environment, base_url FROM corporate_systems ORDER BY name')
            catalog = cur.fetchall()
            cur.execute('''SELECT m.user_id, m.empresa_id, m.role, m.status, u.usuario, e.nome AS company_name
                           FROM corporate_memberships m JOIN usuarios u ON u.id=m.user_id
                           JOIN empresas e ON e.id=m.empresa_id ORDER BY u.usuario,e.nome''')
            rows = cur.fetchall()
            from app import obter_csrf_token
            return render_template('corporate_admin.html', users=users, companies=companies, catalog=catalog, rows=rows, roles=ROLES, environments=ENVIRONMENTS, csrf=obter_csrf_token())


@bp_corporate.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    return response
