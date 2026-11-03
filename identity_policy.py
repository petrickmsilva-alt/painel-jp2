"""One JP2 administrator policy. Callers must pass a freshly loaded database user."""
import os


def configured_admins():
    # Preserve the historical ADMIN_USERS fallback while requiring the DB identity to exist.
    return {name.strip().lower() for name in os.environ.get('ADMIN_USERS', 'petrick').split(',') if name.strip()}


def is_administrator(user):
    if not user or not user.get('id') or not user.get('usuario'):
        return False
    return user.get('perfil') == 'admin' or user['usuario'].lower() in configured_admins()
