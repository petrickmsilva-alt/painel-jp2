"""Reproducible conservative route inventory; classify direct checks, not inferred safety."""
import inspect
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('FLASK_SECRET_KEY', 'inventory-only-not-for-production')
from app import app  # noqa: E402


def classify(rule):
    endpoint = rule.endpoint
    source = inspect.getsource(app.view_functions[endpoint])
    url = rule.rule
    if endpoint.startswith('corporate.'):
        domain = 'Corporate'
        identity = 'DB (usuario recarregado)'
        company = 'membership/contexto DB' if endpoint != 'corporate.manage' else 'alvo validado por FK/DB'
        membership = 'sim' if endpoint != 'corporate.manage' else 'admin global; grant exige ativo'
        risk = 'CONFORME'
    elif endpoint == 'static' or url in ('/manifest.json', '/OneSignalSDKWorker.js'):
        domain, identity, company, membership, risk = 'Estático', 'público', 'N/A', 'não', 'NÃO APLICÁVEL'
    elif url.startswith(('/login', '/logout', '/2fa')):
        domain, identity, company, membership, risk = 'Auth legado', 'DB login / cookie logout' if url in ('/login', '/logout') else 'DB 2FA pendente', 'N/A', 'não', 'PARCIAL'
    else:
        domain = ('Financeiro' if endpoint.startswith('financeiro.') or url.startswith('/financeiro') else
                  'Carteira' if endpoint.startswith('carteira.') else
                  'Eventos' if endpoint.startswith('eventos.') or url.startswith(('/eventos','/api/listar-eventos')) else
                  'Fomentos' if endpoint.startswith('fomentos.') else
                  'Consultoria' if endpoint.startswith('consultoria.') else
                  'Tarefas' if endpoint.startswith('tarefas.') else
                  'Atas' if endpoint.startswith('atas.') else
                  'Admin legado' if url.startswith('/admin/') else
                  'Arquivos/contatos/home')
        identity = ('DB (admin revalidado)' if 'usuario_atual_e_admin(' in source else
                    'cookie (sem revalidar DB)' if 'session' in source else 'verificar função auxiliar')
        membership = 'não'
        if domain == 'Financeiro':
            company = ('empresa_id fornecido pelo cliente' if 'request.form.get("empresa_id")' in source else
                       'empresas globais' if url.startswith(('/api/empresas', '/api/adicionar-empresa', '/api/excluir-empresa')) else
                       'investimentos/empresas sem filtro membership')
            risk = 'NÃO CONFORME'
        elif domain == 'Admin legado':
            company, risk = 'global; não contextual', 'PARCIAL'
        elif domain in ('Consultoria', 'Eventos', 'Fomentos', 'Carteira'):
            company, risk = 'sem filtro membership (avaliar domínio)', 'PARCIAL'
        else:
            company, risk = 'sem filtro membership (compartilhado)', 'PARCIAL'
    return domain, identity, company, membership, risk


rows = []
for rule in sorted(app.url_map.iter_rules(), key=lambda r: (r.rule, r.endpoint)):
    methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
    rows.append((rule.rule, methods, *classify(rule)))
counts = Counter(row[-1] for row in rows)
lines = ['# Matriz completa das rotas Flask registradas', '',
         'Gerada por `python scripts/audit_routes.py` sobre `app.url_map` (inclui rotas novas para comparação).',
         'Classificação conservadora por função registrada e chamadas diretas. Não prova segurança de helpers ou SQL dinâmico.',
         'Identidade `cookie` significa que a função não relê usuário do DB; a proteção CSRF global para writes não substitui autorização.',
         'Rotas operacionais permanecem fora do enforcement corporativo. `NÃO APLICÁVEL` apenas para assets públicos.',
         '', f'Total: {len(rows)} rotas; ' + ', '.join(f'{key}: {value}' for key, value in sorted(counts.items())), '',
         '| Rota | Método | Domínio | Identidade | Empresa | Membership | Risco |',
         '|---|---|---|---|---|---|---|']
for row in rows:
    lines.append('| ' + ' | '.join(str(item).replace('|', '\\|') for item in row) + ' |')
Path('docs/JP2-LEGACY-ROUTE-MATRIX.md').write_text('\n'.join(lines) + '\n')
print(lines[7])
