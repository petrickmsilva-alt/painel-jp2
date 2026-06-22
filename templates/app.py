import os
import uuid
import re
import hashlib
import traceback
import urllib.request
import csv
import io
import time
import secrets
from collections import deque
from bs4 import BeautifulSoup
from urllib.parse import quote, quote_plus, urljoin, urlparse
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, make_response, send_from_directory, send_file, g
from database import get_db_connection
from storage import enviar_arquivo_r2, gerar_url_temporaria_r2, r2_configurado
from werkzeug.security import check_password_hash, generate_password_hash
import pyotp

app = Flask(__name__)

# ConfiguraÃ§Ãµes iniciais
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Defina a variavel FLASK_SECRET_KEY antes de iniciar o painel.")
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_COOKIE_SECURE", "true").lower() != "false",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    SEND_FILE_MAX_AGE_DEFAULT=timedelta(days=7),
)
INDICES_PERFORMANCE_VERIFICADOS = False
COLUNA_PERFIL_USUARIOS_VERIFICADA = False
COLUNAS_2FA_USUARIOS_VERIFICADAS = False
COLUNAS_AGENDA_VERIFICADAS = False
TABELA_CONTATOS_VERIFICADA = False
USUARIOS_ADMIN_CACHE = None
RESUMO_DASHBOARD_CACHE = {"expira_em": None, "dados": None}
LISTAR_CACHE = {}
LISTAR_CACHE_TTL_SEGUNDOS = 12
LOGIN_TENTATIVAS = {}
LOGIN_MAX_TENTATIVAS = 6
LOGIN_BLOQUEIO_SEGUNDOS = 15 * 60
PERFORMANCE_ROTAS = deque(maxlen=160)
ROTAS_MONITORADAS = (
    "/listar",
    "/upload-avancado",
    "/baixar_recurso",
    "/api/resumo-dashboard",
    "/api/listar-eventos",
    "/salvar-site",
)

# Registro do mÃ³dulo financeiro
from financeiro import bp_financeiro
app.register_blueprint(bp_financeiro)

# Registro do módulo de cadastro de eventos
from eventos import bp_eventos
app.register_blueprint(bp_eventos)

# DIRETÃ“RIO LOCAL DE ARMAZENAMENTO
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ConexÃ£o otimizada com o banco
def registrar_log(acao):
    try:
        usuario = session.get('nome_exibicao', 'Sistema / Desconhecido')
        ip_usuario = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO logs_auditoria (usuario, acao, ip_origem)
                VALUES (%s, %s, %s)
            """, (usuario, acao, ip_usuario))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"ERRO AO REGISTRAR LOG: {e}")

def registrar_alerta_seguranca(acao):
    try:
        registrar_log(f"ALERTA DE SEGURANCA: {acao}")
    except Exception:
        print(f"ALERTA DE SEGURANCA: {acao}", flush=True)

def obter_csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token

def validar_csrf_token():
    esperado = session.get("_csrf_token")
    recebido = (
        request.headers.get("X-CSRFToken")
        or request.headers.get("X-CSRF-Token")
        or request.form.get("_csrf_token")
        or request.form.get("csrf_token")
    )
    return bool(esperado and recebido and secrets.compare_digest(str(esperado), str(recebido)))

def criptografar_sha256(senha_pura):
    return hashlib.sha256(senha_pura.encode('utf-8')).hexdigest()

def gerar_hash_senha(senha_pura):
    return generate_password_hash(senha_pura)

def senha_confere(hash_salvo, senha_pura):
    hash_salvo = str(hash_salvo or "")
    if hash_salvo.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(hash_salvo, senha_pura)
    return hash_salvo == criptografar_sha256(senha_pura)

def senha_precisa_atualizar(hash_salvo):
    return not str(hash_salvo or "").startswith(("pbkdf2:", "scrypt:"))

def usuarios_admin():
    global USUARIOS_ADMIN_CACHE
    if USUARIOS_ADMIN_CACHE is not None:
        return USUARIOS_ADMIN_CACHE

    usuarios = os.environ.get("ADMIN_USERS", "petrick")
    USUARIOS_ADMIN_CACHE = {u.strip().lower() for u in usuarios.split(",") if u.strip()}
    return USUARIOS_ADMIN_CACHE

def invalidar_cache_resumo_dashboard():
    RESUMO_DASHBOARD_CACHE["expira_em"] = None
    RESUMO_DASHBOARD_CACHE["dados"] = None

def invalidar_cache_listagem():
    LISTAR_CACHE.clear()

def chave_listagem_cache(bloco, pasta_pai_id):
    pasta_normalizada = str(pasta_pai_id or "").strip()
    if pasta_normalizada in ("", "null", "undefined"):
        pasta_normalizada = "raiz"
    return (str(bloco or ""), pasta_normalizada)

def obter_ip_cliente():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "desconhecido"

def chave_login_tentativa(usuario):
    return f"{obter_ip_cliente()}:{str(usuario or '').lower().strip()}"

def login_esta_bloqueado(usuario):
    dados = LOGIN_TENTATIVAS.get(chave_login_tentativa(usuario))
    if not dados:
        return False
    bloqueado_ate = dados.get("bloqueado_ate")
    if bloqueado_ate and bloqueado_ate > time.time():
        return True
    if bloqueado_ate:
        LOGIN_TENTATIVAS.pop(chave_login_tentativa(usuario), None)
    return False

def registrar_falha_login(usuario):
    chave = chave_login_tentativa(usuario)
    dados = LOGIN_TENTATIVAS.setdefault(chave, {"tentativas": 0, "bloqueado_ate": None})
    dados["tentativas"] += 1
    if dados["tentativas"] >= LOGIN_MAX_TENTATIVAS:
        dados["bloqueado_ate"] = time.time() + LOGIN_BLOQUEIO_SEGUNDOS

def limpar_falhas_login(usuario):
    LOGIN_TENTATIVAS.pop(chave_login_tentativa(usuario), None)

def data_iso_ou_none(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None

def rota_monitorada(caminho):
    return any(caminho.startswith(prefixo) for prefixo in ROTAS_MONITORADAS)

def resumo_performance_rotas():
    agrupado = {}
    for item in PERFORMANCE_ROTAS:
        rota = item["rota"]
        dados = agrupado.setdefault(rota, {"rota": rota, "qtd": 0, "total_ms": 0, "max_ms": 0})
        dados["qtd"] += 1
        dados["total_ms"] += item["ms"]
        dados["max_ms"] = max(dados["max_ms"], item["ms"])

    resumo = []
    for dados in agrupado.values():
        resumo.append({
            "rota": dados["rota"],
            "qtd": dados["qtd"],
            "media_ms": round(dados["total_ms"] / max(dados["qtd"], 1), 1),
            "max_ms": round(dados["max_ms"], 1),
        })
    return sorted(resumo, key=lambda item: item["media_ms"], reverse=True)

def garantir_coluna_perfil_usuarios():
    global COLUNA_PERFIL_USUARIOS_VERIFICADA
    if COLUNA_PERFIL_USUARIOS_VERIFICADA:
        return

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM usuarios LIKE 'perfil'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE usuarios ADD COLUMN perfil VARCHAR(20) NOT NULL DEFAULT 'socio'")
                for usuario in usuarios_admin():
                    cur.execute("UPDATE usuarios SET perfil = 'admin' WHERE usuario = %s", (usuario,))
        COLUNA_PERFIL_USUARIOS_VERIFICADA = True
    finally:
        conn.close()

def garantir_colunas_2fa_usuarios():
    global COLUNAS_2FA_USUARIOS_VERIFICADAS
    if COLUNAS_2FA_USUARIOS_VERIFICADAS:
        return

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM usuarios LIKE 'otp_secret'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE usuarios ADD COLUMN otp_secret VARCHAR(64) NULL")
            cur.execute("SHOW COLUMNS FROM usuarios LIKE 'otp_enabled'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE usuarios ADD COLUMN otp_enabled TINYINT(1) NOT NULL DEFAULT 0")
        COLUNAS_2FA_USUARIOS_VERIFICADAS = True
    finally:
        conn.close()

def usuario_login_e_admin(user):
    if not user:
        return False
    usuario = str(user.get("usuario") or "").lower()
    return usuario in usuarios_admin() or (user.get("perfil") == "admin")

def finalizar_login_usuario(user):
    session.pop("2fa_pending_user", None)
    session.pop("2fa_pending_nome", None)
    session.pop("2fa_pending_perfil", None)
    session.pop("2fa_temp_secret", None)
    session['usuario_logado'] = user['usuario']
    session['nome_exibicao'] = user.get('nome_exibicao', user['usuario'])
    session['perfil_usuario'] = user.get('perfil') or obter_perfil_usuario(user['usuario']) or 'socio'
    session.permanent = True
    limpar_falhas_login(user['usuario'])
    registrar_log("Realizou login no sistema")

def iniciar_fluxo_2fa(user):
    session['2fa_pending_user'] = user['usuario']
    session['2fa_pending_nome'] = user.get('nome_exibicao', user['usuario'])
    session['2fa_pending_perfil'] = user.get('perfil') or 'admin'

def usuario_2fa_pendente():
    usuario = session.get("2fa_pending_user")
    if not usuario:
        return None
    garantir_colunas_2fa_usuarios()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM usuarios WHERE usuario = %s", (usuario,))
            return cur.fetchone()
    finally:
        conn.close()

def obter_perfil_usuario(usuario):
    if not usuario:
        return None

    garantir_coluna_perfil_usuarios()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT perfil FROM usuarios WHERE usuario = %s", (usuario,))
            dados = cur.fetchone()
            return dados.get("perfil") if dados else None
    finally:
        conn.close()

def usuario_atual_e_admin():
    usuario = session.get("usuario_logado", "").lower()
    if usuario in usuarios_admin():
        return True

    perfil_sessao = session.get("perfil_usuario")
    if perfil_sessao:
        return perfil_sessao == "admin"

    return obter_perfil_usuario(usuario) == "admin"

def acesso_negado():
    registrar_log("Tentou acessar uma area restrita de administrador")
    return render_template("acesso_negado.html"), 403

def garantir_colunas_agenda():
    global COLUNAS_AGENDA_VERIFICADAS
    if COLUNAS_AGENDA_VERIFICADAS:
        return

    colunas = {
        "tipo_evento": "VARCHAR(20) NOT NULL DEFAULT 'reuniao'",
        "local_evento": "VARCHAR(255) NULL",
        "horario": "VARCHAR(10) NULL",
        "criado_por": "VARCHAR(120) NULL",
    }
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for coluna, definicao in colunas.items():
                cur.execute("SHOW COLUMNS FROM agenda_eventos LIKE %s", (coluna,))
                if not cur.fetchone():
                    cur.execute(f"ALTER TABLE agenda_eventos ADD COLUMN {coluna} {definicao}")
        COLUNAS_AGENDA_VERIFICADAS = True
    finally:
        conn.close()

def garantir_tabela_contatos():
    global TABELA_CONTATOS_VERIFICADA
    if TABELA_CONTATOS_VERIFICADA:
        return

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS contatos_telefonicos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome VARCHAR(160) NOT NULL,
                    empresa VARCHAR(160) NULL,
                    cargo VARCHAR(120) NULL,
                    telefone VARCHAR(40) NULL,
                    whatsapp VARCHAR(40) NULL,
                    email VARCHAR(160) NULL,
                    categoria VARCHAR(40) NOT NULL DEFAULT 'geral',
                    observacoes TEXT NULL,
                    criado_por VARCHAR(120) NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            criar_indice_se_necessario(cur, "contatos_telefonicos", "idx_contatos_busca", "nome(120), empresa(120), categoria(40)")
            criar_indice_se_necessario(cur, "contatos_telefonicos", "idx_contatos_categoria", "categoria(40), nome(120)")
        TABELA_CONTATOS_VERIFICADA = True
    finally:
        conn.close()

def limpar_telefone(valor):
    return re.sub(r"\D+", "", str(valor or ""))

def formatar_telefone_br(valor):
    digitos = limpar_telefone(valor)
    if not digitos:
        return ""

    if digitos.startswith("0055"):
        digitos = digitos[4:]
    elif digitos.startswith("55") and len(digitos) > 11:
        digitos = digitos[2:]

    digitos = digitos[:11]

    if len(digitos) < 10:
        return str(valor or "").strip()

    ddd = digitos[:2]
    numero = digitos[2:]
    if len(numero) == 9:
        return f"+55 {ddd} {numero[:5]}-{numero[5:]}"
    if len(numero) == 8:
        return f"+55 {ddd} {numero[:4]}-{numero[4:]}"
    return f"+55 {ddd} {numero}"

def criar_indice_se_necessario(cur, tabela, nome_indice, definicao_colunas):
    if not re.match(r"^[A-Za-z0-9_]+$", tabela) or not re.match(r"^[A-Za-z0-9_]+$", nome_indice):
        raise ValueError("Nome de tabela ou indice invalido")

    cur.execute("""
        SELECT COUNT(1) AS total
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
    """, (tabela, nome_indice))
    dados = cur.fetchone() or {}
    if int(dados.get("total", 0)) == 0:
        cur.execute(f"CREATE INDEX `{nome_indice}` ON `{tabela}` ({definicao_colunas})")

def garantir_indices_performance():
    indices = [
        ("arquivos_painel", "idx_arquivos_listagem", "bloco(50), pasta_pai_id, deletado, tipo(20), nome_original(191)"),
        ("arquivos_painel", "idx_arquivos_pasta_nome", "bloco(50), nome_original(191), tipo(20), deletado"),
        ("arquivos_painel", "idx_arquivos_resumo", "tipo(20), deletado"),
        ("logs_auditoria", "idx_logs_data_registro", "data_registro"),
        ("agenda_eventos", "idx_agenda_data_evento", "data_evento"),
        ("usuarios", "idx_usuarios_usuario", "usuario(80)"),
        ("empresas", "idx_empresas_nome", "nome(120)"),
        ("investimentos", "idx_investimentos_empresa_datas", "empresa_id, data_inicio, data_pgto"),
        ("investimentos", "idx_investimentos_credor", "nome_investidor(120)"),
        ("investimentos", "idx_investimentos_captador", "captador(120)"),
        ("investimento_pagamentos", "idx_pagamentos_investimento_data", "investimento_id, data_pagamento"),
        ("eventos_cadastro", "idx_eventos_data_cidade", "data_inicio, cidade(120), uf(2)"),
        ("eventos_custos", "idx_eventos_custos_evento", "evento_id"),
    ]

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for tabela, nome_indice, definicao_colunas in indices:
                try:
                    criar_indice_se_necessario(cur, tabela, nome_indice, definicao_colunas)
                except Exception as e:
                    print(f"AVISO: indice {nome_indice} nao foi aplicado: {e}", flush=True)
    finally:
        conn.close()

@app.before_request
def preparar_performance_banco():
    global INDICES_PERFORMANCE_VERIFICADOS
    if INDICES_PERFORMANCE_VERIFICADOS or request.endpoint == "static":
        return

    INDICES_PERFORMANCE_VERIFICADOS = True
    try:
        garantir_indices_performance()
    except Exception as e:
        print(f"AVISO: nao foi possivel verificar/criar indices de performance: {e}", flush=True)

@app.before_request
def iniciar_medicao_performance():
    g.inicio_request = time.perf_counter()

@app.before_request
def proteger_requisicoes_de_escrita():
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return

    origem = request.headers.get("Origin") or request.headers.get("Referer")
    if origem:
        host_origem = urlparse(origem).netloc
        if host_origem and host_origem != request.host:
            registrar_alerta_seguranca(f"Origem externa bloqueada em {request.path}: {host_origem}")
            return jsonify({"status": "erro", "mensagem": "Origem da requisicao nao autorizada."}), 403

    if not validar_csrf_token():
        registrar_alerta_seguranca(f"CSRF invalido em {request.path}")
        return jsonify({"status": "erro", "mensagem": "Sessao expirada ou token de seguranca invalido. Atualize a pagina e tente novamente."}), 403

def script_csrf_html():
    token = obter_csrf_token()
    return f'''<meta name="csrf-token" content="{token}">
<script>
(function() {{
  const meta = document.querySelector('meta[name="csrf-token"]');
  const token = meta ? meta.getAttribute('content') : '';
  if (!token) return;
  const unsafe = new Set(['POST','PUT','PATCH','DELETE']);
  function isPainelSearchField(input) {{
    if (!input || input.tagName !== 'INPUT') return false;
    const type = (input.getAttribute('type') || 'text').toLowerCase();
    if (!['search','text',''].includes(type)) return false;
    const metaBusca = [
      input.id || '',
      input.name || '',
      input.placeholder || '',
      input.className || '',
      input.getAttribute('aria-label') || ''
    ].join(' ').toLowerCase();
    return type === 'search'
      || !!input.closest('.dataTables_filter')
      || /(busca|buscar|pesquisa|pesquisar|search|filtro|procurar)/i.test(metaBusca);
  }}
  function hardenSearchField(input) {{
    if (!isPainelSearchField(input)) return;
    input.setAttribute('autocomplete', 'new-password');
    input.setAttribute('autocorrect', 'off');
    input.setAttribute('autocapitalize', 'off');
    input.setAttribute('spellcheck', 'false');
    input.setAttribute('data-lpignore', 'true');
    input.setAttribute('data-form-type', 'other');
    if (!input.dataset.jp2SearchGuard) {{
      input.dataset.jp2SearchGuard = '1';
      input.addEventListener('input', function() {{
        if (input.dataset.jp2Clearing !== '1') input.dataset.jp2SearchTouched = '1';
      }});
      input.addEventListener('focus', function() {{
        input.dataset.jp2SearchTouched = '1';
      }});
    }}
  }}
  function clearSearchField(input, force) {{
    if (!isPainelSearchField(input)) return;
    hardenSearchField(input);
    if (!force && (document.activeElement === input || input.dataset.jp2SearchTouched === '1')) return;
    if (input.value || input.defaultValue || input.getAttribute('value')) {{
      input.dataset.jp2Clearing = '1';
      input.value = '';
      input.defaultValue = '';
      input.removeAttribute('value');
      input.dispatchEvent(new Event('input', {{ bubbles: true }}));
      input.dispatchEvent(new Event('change', {{ bubbles: true }}));
      setTimeout(function() {{ delete input.dataset.jp2Clearing; }}, 0);
    }}
  }}
  function protectAndClearSearchFields(force) {{
    document.querySelectorAll('input').forEach(function(input) {{
      hardenSearchField(input);
      clearSearchField(input, !!force);
    }});
  }}
  function scheduleSearchCleanup() {{
    protectAndClearSearchFields(true);
    [80, 250, 700, 1500, 3000, 6000].forEach(function(ms) {{
      setTimeout(function() {{ protectAndClearSearchFields(false); }}, ms);
    }});
  }}
  function sameOrigin(url) {{
    try {{ return new URL(url, window.location.href).origin === window.location.origin; }}
    catch (e) {{ return true; }}
  }}
  function addTokenToForms() {{
    document.querySelectorAll('form').forEach(form => {{
      const method = (form.getAttribute('method') || 'GET').toUpperCase();
      if (!unsafe.has(method)) return;
      if (!form.querySelector('input[name="_csrf_token"]')) {{
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = '_csrf_token';
        input.value = token;
        form.appendChild(input);
      }}
    }});
  }}
  const originalFetch = window.fetch;
  window.fetch = function(input, init) {{
    init = init || {{}};
    const method = (init.method || (input && input.method) || 'GET').toUpperCase();
    const url = typeof input === 'string' ? input : (input && input.url) || window.location.href;
    if (unsafe.has(method) && sameOrigin(url)) {{
      const headers = new Headers(init.headers || (input && input.headers) || {{}});
      headers.set('X-CSRFToken', token);
      init.headers = headers;
    }}
    return originalFetch(input, init);
  }};
  const open = XMLHttpRequest.prototype.open;
  const send = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(method, url) {{
    this.__csrfMethod = (method || 'GET').toUpperCase();
    this.__csrfUrl = url;
    return open.apply(this, arguments);
  }};
  XMLHttpRequest.prototype.send = function() {{
    if (unsafe.has(this.__csrfMethod || 'GET') && sameOrigin(this.__csrfUrl || window.location.href)) {{
      this.setRequestHeader('X-CSRFToken', token);
    }}
    return send.apply(this, arguments);
  }};
  document.addEventListener('DOMContentLoaded', addTokenToForms);
  document.addEventListener('DOMContentLoaded', scheduleSearchCleanup);
  document.addEventListener('submit', addTokenToForms, true);
  window.addEventListener('pageshow', scheduleSearchCleanup);
  new MutationObserver(function(mutations) {{
    mutations.forEach(function(mutation) {{
      mutation.addedNodes.forEach(function(node) {{
        if (!node || node.nodeType !== 1) return;
        if (node.matches && node.matches('input')) clearSearchField(node, true);
        if (node.querySelectorAll) node.querySelectorAll('input').forEach(function(input) {{ clearSearchField(input, true); }});
      }});
    }});
  }}).observe(document.documentElement, {{ childList: true, subtree: true }});
}})();
</script>'''

@app.after_request
def injetar_csrf_em_html(response):
    tipo = response.headers.get("Content-Type", "")
    if response.direct_passthrough or "text/html" not in tipo:
        return response
    try:
        html = response.get_data(as_text=True)
        if 'name="csrf-token"' not in html and "</head>" in html:
            html = html.replace("</head>", script_csrf_html() + "\n</head>", 1)
            response.set_data(html)
            response.headers["Content-Length"] = str(len(response.get_data()))
    except Exception as e:
        print(f"AVISO: nao foi possivel injetar CSRF: {e}", flush=True)
    return response

@app.after_request
def finalizar_medicao_performance(response):
    inicio = getattr(g, "inicio_request", None)
    if inicio is None:
        return response

    duracao_ms = round((time.perf_counter() - inicio) * 1000, 1)
    response.headers["X-Response-Time-ms"] = str(duracao_ms)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    caminho = request.path
    if rota_monitorada(caminho) or duracao_ms >= 1000:
        PERFORMANCE_ROTAS.append({
            "horario": datetime.now().strftime("%H:%M:%S"),
            "metodo": request.method,
            "rota": caminho,
            "status": response.status_code,
            "ms": duracao_ms,
        })

    return response

def nome_base_imagem_site(nome):
    return "".join(x for x in str(nome or "") if x.isalnum())

def arquivo_office(nome_arquivo):
    extensao = os.path.splitext(str(nome_arquivo or "").lower())[1]
    return extensao in {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}

def imagem_site_existente(nome):
    nome_limpo = nome_base_imagem_site(nome)
    if not nome_limpo:
        return "/static/image/ibd.jpeg"

    pasta_imagens = os.path.join(app.root_path, 'static', 'image')
    for extensao in ["png", "jpg", "jpeg", "webp", "svg", "ico"]:
        caminho = os.path.join(pasta_imagens, f"{nome_limpo}.{extensao}")
        if os.path.exists(caminho):
            return f"/static/image/{nome_limpo}.{extensao}"

    return f"/static/image/{nome_limpo}.jpeg"

def caminho_static_existe(caminho_publico):
    if not caminho_publico or not caminho_publico.startswith("/static/"):
        return False
    caminho_relativo = caminho_publico.lstrip("/").replace("/", os.sep)
    return os.path.exists(os.path.join(app.root_path, caminho_relativo))

def formatar_item_painel(linha):
    return {
        'id': linha['id'],
        'nome': linha['nome_original'],
        'tipo': linha['tipo'],
        'caminho': linha.get('caminho_sistema'),
        'imagem_bg': imagem_site_existente(linha.get('nome_original', '')) if linha.get('tipo') == 'link' else '',
        'autor': linha.get('criado_por') or 'Sistema',
        'bloco': linha.get('bloco'),
        'categoria': linha.get('categoria'),
        'pasta_pai_id': linha.get('pasta_pai_id')
    }

def extensao_por_tipo_conteudo(content_type, url_imagem):
    content_type = str(content_type or "").split(";")[0].strip().lower()
    mapa = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
        "image/svg+xml": "svg",
        "image/x-icon": "ico",
        "image/vnd.microsoft.icon": "ico",
    }
    if content_type in mapa:
        return mapa[content_type]

    caminho = urlparse(url_imagem).path.lower()
    for extensao in ["png", "jpg", "jpeg", "webp", "svg", "ico"]:
        if caminho.endswith(f".{extensao}"):
            return "jpg" if extensao == "jpeg" else extensao
    return None

def capturar_logo_site(nome, url):
    nome_limpo = nome_base_imagem_site(nome)
    if not nome_limpo:
        return None

    pasta_imagens = os.path.join(app.root_path, 'static', 'image')
    os.makedirs(pasta_imagens, exist_ok=True)
    candidatos = []

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=6).read()
        soup = BeautifulSoup(html, 'html.parser')

        for meta_seletor in [
            {"property": "og:image"},
            {"name": "twitter:image"},
            {"property": "og:logo"},
        ]:
            meta = soup.find("meta", attrs=meta_seletor)
            if meta and meta.get("content"):
                candidatos.append((1000, urljoin(url, meta.get("content"))))

        for link in soup.find_all("link"):
            rel = " ".join(link.get("rel", [])) if isinstance(link.get("rel"), list) else str(link.get("rel", ""))
            href = link.get("href")
            if not href:
                continue
            rel_lower = rel.lower()
            if "icon" not in rel_lower and "apple-touch-icon" not in rel_lower:
                continue

            prioridade = 500
            tamanhos = re.findall(r"(\d+)x(\d+)", str(link.get("sizes", "")))
            if tamanhos:
                prioridade += max(int(largura) for largura, _ in tamanhos)
            if "apple-touch-icon" in rel_lower:
                prioridade += 80
            candidatos.append((prioridade, urljoin(url, href)))
    except Exception as e:
        print(f"Nao foi possivel ler a pagina para capturar logo: {e}")

    candidatos.append((100, urljoin(url, "/favicon.ico")))
    candidatos.append((50, f"https://www.google.com/s2/favicons?sz=128&domain_url={quote_plus(url)}"))

    vistos = set()
    for _, url_imagem in sorted(candidatos, key=lambda item: item[0], reverse=True):
        if not url_imagem or url_imagem in vistos:
            continue
        vistos.add(url_imagem)
        try:
            req_img = urllib.request.Request(
                url_imagem,
                headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'image/avif,image/webp,image/png,image/svg+xml,image/*,*/*;q=0.8'
                }
            )
            with urllib.request.urlopen(req_img, timeout=6) as resposta:
                content_type = resposta.headers.get("Content-Type", "")
                extensao = extensao_por_tipo_conteudo(content_type, url_imagem)
                if not extensao:
                    continue
                conteudo = resposta.read(2 * 1024 * 1024)
                if len(conteudo) < 80:
                    continue

            caminho_salvar = os.path.join(pasta_imagens, f"{nome_limpo}.{extensao}")
            with open(caminho_salvar, "wb") as arquivo_logo:
                arquivo_logo.write(conteudo)
            return f"/static/image/{nome_limpo}.{extensao}"
        except Exception as e:
            print(f"Falha ao baixar logo {url_imagem}: {e}")

    return None

@app.context_processor
def contexto_global():
    return {"usuario_e_admin": usuario_atual_e_admin()}
    
@app.route('/')
def home():
    if 'usuario_logado' not in session: 
        return redirect(url_for('tela_login'))

    return render_template('home.html', nome_socio=session.get('nome_exibicao', 'Sócio'))

@app.route('/carteira-investimentos')
def carteira_investimentos():
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))

    url_modulo = os.environ.get("CARTEIRA_INVESTIMENTOS_URL", "").strip()
    if url_modulo:
        return redirect(url_modulo)

    return render_template(
        'carteira_investimentos.html',
        nome_socio=session.get('nome_exibicao', 'Sócio')
    )

@app.route('/login', methods=['GET', 'POST'])
def tela_login():
    if request.method == 'GET' and 'usuario_logado' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        u = request.form.get('usuario', '').lower().strip()
        s = request.form.get('senha', '').strip()

        if login_esta_bloqueado(u):
            registrar_log(f"Login bloqueado temporariamente para o usuario {u}")
            flash("Muitas tentativas incorretas. Aguarde alguns minutos e tente novamente.")
            return redirect(url_for('tela_login'))

        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM usuarios WHERE usuario = %s", (u,))
                user = cur.fetchone()

                if user and senha_confere(user.get('senha'), s):
                    if senha_precisa_atualizar(user.get('senha')):
                        cur.execute(
                            "UPDATE usuarios SET senha = %s WHERE usuario = %s",
                            (gerar_hash_senha(s), user['usuario'])
                        )

                    if usuario_login_e_admin(user):
                        garantir_colunas_2fa_usuarios()
                        iniciar_fluxo_2fa(user)
                        if user.get("otp_enabled") and user.get("otp_secret"):
                            return redirect(url_for('verificar_2fa'))
                        return redirect(url_for('configurar_2fa'))

                    finalizar_login_usuario(user)
                    return redirect(url_for('home'))

                registrar_falha_login(u)
                flash("Usuario ou senha incorretos.")
        except Exception as e:
            print(f"Erro no Login: {e}")
            flash(f"Erro de conexão com o banco: {str(e)}")
            return redirect(url_for('tela_login'))
        finally:
            if conn:
                conn.close()

    return render_template('login.html')

@app.route('/2fa/configurar', methods=['GET', 'POST'])
def configurar_2fa():
    user = usuario_2fa_pendente()
    if not user:
        return redirect(url_for('tela_login'))

    secret = session.get("2fa_temp_secret") or pyotp.random_base32()
    session["2fa_temp_secret"] = secret
    totp = pyotp.TOTP(secret)
    otpauth_uri = totp.provisioning_uri(
        name=user.get("usuario"),
        issuer_name="JP2 Business"
    )

    if request.method == 'POST':
        codigo = request.form.get("codigo", "").strip().replace(" ", "")
        if totp.verify(codigo, valid_window=1):
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE usuarios SET otp_secret = %s, otp_enabled = 1 WHERE usuario = %s",
                        (secret, user["usuario"])
                    )
                conn.commit()
            finally:
                conn.close()
            finalizar_login_usuario(user)
            registrar_log("Configurou autenticacao em duas etapas")
            return redirect(url_for('home'))
        flash("Codigo 2FA invalido. Confira o aplicativo autenticador e tente novamente.")

    return render_template("2fa.html", modo="configurar", secret=secret, otpauth_uri=otpauth_uri)

@app.route('/2fa/verificar', methods=['GET', 'POST'])
def verificar_2fa():
    user = usuario_2fa_pendente()
    if not user:
        return redirect(url_for('tela_login'))

    if request.method == 'POST':
        codigo = request.form.get("codigo", "").strip().replace(" ", "")
        secret = user.get("otp_secret")
        if secret and pyotp.TOTP(secret).verify(codigo, valid_window=1):
            finalizar_login_usuario(user)
            registrar_log("Validou autenticacao em duas etapas")
            return redirect(url_for('home'))
        registrar_alerta_seguranca(f"Codigo 2FA invalido para usuario {user.get('usuario')}")
        flash("Codigo 2FA invalido.")

    return render_template("2fa.html", modo="verificar", secret=None, otpauth_uri=None)

@app.route('/logout')
def logout():
    registrar_log("Realizou logout no sistema")
    session.clear()
    return redirect(url_for('tela_login'))

@app.route('/agenda')
def pagina_agenda():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    return render_template('agenda.html', nome_socio=session.get('nome_exibicao', 'Socio'))

@app.route('/compromissos')
def pagina_compromissos():
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))
    garantir_colunas_agenda()
    return render_template('compromissos.html', nome_socio=session.get('nome_exibicao', 'Socio'))

@app.route('/contatos')
def pagina_contatos():
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))

    garantir_tabela_contatos()
    busca = request.args.get('q', '').strip()
    categoria = request.args.get('categoria', '').strip()
    categorias_validas = ['geral', 'cliente', 'fornecedor', 'parceiro', 'evento', 'institucional', 'pessoal']

    filtros = []
    params = []
    if busca:
        termo = f"%{busca}%"
        filtros.append("(nome LIKE %s OR empresa LIKE %s OR cargo LIKE %s OR telefone LIKE %s OR whatsapp LIKE %s OR email LIKE %s)")
        params.extend([termo, termo, termo, termo, termo, termo])
    if categoria in categorias_validas:
        filtros.append("categoria = %s")
        params.append(categoria)

    where_sql = f"WHERE {' AND '.join(filtros)}" if filtros else ""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id, nome, empresa, cargo, telefone, whatsapp, email, categoria, observacoes, criado_por, criado_em, atualizado_em
                FROM contatos_telefonicos
                {where_sql}
                ORDER BY nome ASC
                LIMIT 120
            """, tuple(params))
            contatos = cur.fetchall()
    finally:
        conn.close()

    for contato in contatos:
        contato['telefone'] = formatar_telefone_br(contato.get('telefone')) or contato.get('telefone')
        contato['whatsapp'] = formatar_telefone_br(contato.get('whatsapp')) or contato.get('whatsapp')
        numero = limpar_telefone(contato.get('whatsapp') or contato.get('telefone'))
        if numero and len(numero) in (10, 11):
            numero = "55" + numero
        contato['whatsapp_link'] = numero
        contato['telefone_link'] = limpar_telefone(contato.get('telefone') or contato.get('whatsapp'))

    return render_template(
        'contatos.html',
        contatos=contatos,
        busca=busca,
        categoria_atual=categoria,
        categorias=categorias_validas,
        limite_contatos=120,
        nome_socio=session.get('nome_exibicao', 'Socio')
    )

@app.route('/contatos/adicionar', methods=['POST'])
def adicionar_contato():
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))

    garantir_tabela_contatos()
    nome = request.form.get('nome', '').strip()
    if not nome:
        flash("Informe o nome do contato.")
        return redirect(url_for('pagina_contatos'))

    categoria = request.form.get('categoria', 'geral')
    if categoria not in ['geral', 'cliente', 'fornecedor', 'parceiro', 'evento', 'institucional', 'pessoal']:
        categoria = 'geral'
    telefone = formatar_telefone_br(request.form.get('telefone', ''))
    whatsapp = formatar_telefone_br(request.form.get('whatsapp', ''))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO contatos_telefonicos
                (nome, empresa, cargo, telefone, whatsapp, email, categoria, observacoes, criado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                nome,
                request.form.get('empresa', '').strip(),
                request.form.get('cargo', '').strip(),
                telefone,
                whatsapp,
                request.form.get('email', '').strip(),
                categoria,
                request.form.get('observacoes', '').strip(),
                session.get('nome_exibicao', 'Sistema')
            ))
        conn.commit()
        registrar_log(f"Cadastrou contato telefonico: {nome}")
        flash("Contato cadastrado com sucesso.")
    finally:
        conn.close()

    return redirect(url_for('pagina_contatos'))

@app.route('/contatos/editar/<int:contato_id>', methods=['POST'])
def editar_contato(contato_id):
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))

    categoria = request.form.get('categoria', 'geral')
    if categoria not in ['geral', 'cliente', 'fornecedor', 'parceiro', 'evento', 'institucional', 'pessoal']:
        categoria = 'geral'

    nome = request.form.get('nome', '').strip()
    if not nome:
        flash("Informe o nome do contato.")
        return redirect(url_for('pagina_contatos'))

    telefone = formatar_telefone_br(request.form.get('telefone', ''))
    whatsapp = formatar_telefone_br(request.form.get('whatsapp', ''))

    garantir_tabela_contatos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE contatos_telefonicos
                SET nome = %s, empresa = %s, cargo = %s, telefone = %s, whatsapp = %s,
                    email = %s, categoria = %s, observacoes = %s
                WHERE id = %s
            """, (
                nome,
                request.form.get('empresa', '').strip(),
                request.form.get('cargo', '').strip(),
                telefone,
                whatsapp,
                request.form.get('email', '').strip(),
                categoria,
                request.form.get('observacoes', '').strip(),
                contato_id
            ))
        conn.commit()
        registrar_log(f"Atualizou contato telefonico ID: {contato_id}")
        flash("Contato atualizado com sucesso.")
    finally:
        conn.close()

    return redirect(url_for('pagina_contatos'))

@app.route('/contatos/excluir/<int:contato_id>', methods=['POST'])
def excluir_contato(contato_id):
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))

    garantir_tabela_contatos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contatos_telefonicos WHERE id = %s", (contato_id,))
        conn.commit()
        registrar_log(f"Removeu contato telefonico ID: {contato_id}")
        flash("Contato removido com sucesso.")
    finally:
        conn.close()

    return redirect(url_for('pagina_contatos'))

@app.route('/admin/usuarios', methods=['GET', 'POST'])
def admin_usuarios():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    if not usuario_atual_e_admin():
        return acesso_negado()
    
    if request.method == 'POST':
        novo_user = request.form.get('novo_usuario', '').lower().strip()
        senha_pura = request.form.get('nova_senha', '').strip()
        nome_exib = request.form.get('nome_exibicao', '')
        perfil = request.form.get('perfil', 'socio')
        if perfil not in ['admin', 'socio', 'leitura']:
            perfil = 'socio'
        senha_cripto = gerar_hash_senha(senha_pura)
        
        try:
            garantir_coluna_perfil_usuarios()
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usuarios (usuario, senha, nome_exibicao, perfil)
                    VALUES (%s, %s, %s, %s)
                """, (novo_user, senha_cripto, nome_exib, perfil))
            conn.commit()
            conn.close()
            invalidar_cache_resumo_dashboard()
            registrar_log(f"Cadastrou um novo usuário no painel: {novo_user}")
        except Exception as e:
            print(f"Erro cadastro: {e}")
            
    conn = get_db_connection()
    with conn.cursor() as cur:
        garantir_coluna_perfil_usuarios()
        cur.execute("SELECT id, usuario, nome_exibicao, perfil FROM usuarios ORDER BY perfil, nome_exibicao")
        lista_usuarios = cur.fetchall()
    conn.close()
    return render_template('admin_usuarios.html', usuarios=lista_usuarios)

@app.route('/admin/excluir_usuario/<int:usuario_id>', methods=['POST'])
def excluir_usuario(usuario_id):
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    if not usuario_atual_e_admin():
        return acesso_negado()
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT usuario, perfil FROM usuarios WHERE id = %s", (usuario_id,))
            usuario_alvo = cur.fetchone()
            if usuario_alvo and usuario_alvo.get('usuario') == session.get('usuario_logado'):
                flash("Você não pode excluir seu próprio usuário.")
                conn.close()
                return redirect(url_for('admin_usuarios'))
            cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conn.commit()
        conn.close()
        invalidar_cache_resumo_dashboard()
        registrar_log(f"Removeu o usuário ID: {usuario_id} do sistema")
        flash("Sócio removido com sucesso!")
    except Exception as e:
        print(f"Erro ao deletar usuário: {e}")
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/alterar_perfil/<int:usuario_id>', methods=['POST'])
def alterar_perfil_usuario(usuario_id):
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    if not usuario_atual_e_admin():
        return acesso_negado()

    novo_perfil = request.form.get('perfil', 'socio')
    if novo_perfil not in ['admin', 'socio', 'leitura']:
        flash("Perfil inválido.")
        return redirect(url_for('admin_usuarios'))

    try:
        garantir_coluna_perfil_usuarios()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT usuario, perfil FROM usuarios WHERE id = %s", (usuario_id,))
            usuario_alvo = cur.fetchone()
            if not usuario_alvo:
                flash("Usuário não encontrado.")
                conn.close()
                return redirect(url_for('admin_usuarios'))

            if usuario_alvo.get('usuario') == session.get('usuario_logado') and novo_perfil != 'admin':
                flash("Você não pode remover seu próprio perfil de administrador.")
                conn.close()
                return redirect(url_for('admin_usuarios'))

            cur.execute("UPDATE usuarios SET perfil = %s WHERE id = %s", (novo_perfil, usuario_id))
        conn.close()
        registrar_log(f"Alterou perfil do usuário {usuario_alvo.get('usuario')} para {novo_perfil}")
        flash("Perfil atualizado com sucesso.")
    except Exception as e:
        print(f"Erro ao alterar perfil: {e}")
        flash("Não foi possível atualizar o perfil.")

    return redirect(url_for('admin_usuarios'))

@app.route('/admin/alterar_senha/<int:usuario_id>', methods=['POST'])
def alterar_senha_usuario(usuario_id):
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    if not usuario_atual_e_admin():
        return acesso_negado()

    nova_senha = request.form.get('nova_senha', '').strip()
    confirmar_senha = request.form.get('confirmar_senha', '').strip()

    if len(nova_senha) < 8:
        flash("A nova senha precisa ter pelo menos 8 caracteres.")
        return redirect(url_for('admin_usuarios'))

    if nova_senha != confirmar_senha:
        flash("A confirmação da senha não confere.")
        return redirect(url_for('admin_usuarios'))

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT usuario FROM usuarios WHERE id = %s", (usuario_id,))
            usuario_alvo = cur.fetchone()
            if not usuario_alvo:
                flash("Usuário não encontrado.")
                conn.close()
                return redirect(url_for('admin_usuarios'))

            cur.execute(
                "UPDATE usuarios SET senha = %s WHERE id = %s",
                (gerar_hash_senha(nova_senha), usuario_id)
            )
        conn.close()
        registrar_log(f"Alterou a senha do usuário {usuario_alvo.get('usuario')}")
        flash("Senha atualizada com sucesso.")
    except Exception as e:
        print(f"Erro ao alterar senha: {e}")
        flash("Não foi possível alterar a senha.")

    return redirect(url_for('admin_usuarios'))

@app.route('/admin/logs')
def admin_logs():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    if not usuario_atual_e_admin():
        return acesso_negado()
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM logs_auditoria ORDER BY data_registro DESC LIMIT 250")
            lista_logs = cur.fetchall()
        conn.close()
    except:
        lista_logs = []

    hoje = datetime.now().date()
    usuarios = set()
    logs_hoje = 0
    exclusoes = 0
    criacoes = 0
    acessos = 0

    for log in lista_logs:
        usuario_log = str(log.get('usuario') or '').strip()
        acao_log = str(log.get('acao') or '').lower()
        if usuario_log:
            usuarios.add(usuario_log)

        data_log = log.get('data_registro')
        if hasattr(data_log, 'date') and data_log.date() == hoje:
            logs_hoje += 1

        if any(palavra in acao_log for palavra in ['apagou', 'removeu', 'excluiu', 'deletou']):
            exclusoes += 1
        elif any(palavra in acao_log for palavra in ['criou', 'adicionou', 'cadastrou', 'incluiu', 'upload']):
            criacoes += 1
        elif any(palavra in acao_log for palavra in ['login', 'logout', 'acessou', 'tentou acessar']):
            acessos += 1

    resumo_logs = {
        'total': len(lista_logs),
        'hoje': logs_hoje,
        'usuarios': len(usuarios),
        'exclusoes': exclusoes,
        'criacoes': criacoes,
        'acessos': acessos,
    }

    return render_template('admin_logs.html', logs=lista_logs, resumo=resumo_logs)

@app.route('/admin/logs/exportar')
def exportar_logs_auditoria():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    if not usuario_atual_e_admin():
        return acesso_negado()

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT data_registro, usuario, acao, ip_origem FROM logs_auditoria ORDER BY data_registro DESC LIMIT 1000")
            lista_logs = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"Erro ao exportar logs: {e}")
        lista_logs = []

    saida = io.StringIO()
    saida.write('\ufeff')
    writer = csv.writer(saida, delimiter=';')
    writer.writerow(['Data/Hora', 'Usuario', 'Acao executada', 'IP de origem'])
    for log in lista_logs:
        writer.writerow([
            log.get('data_registro'),
            log.get('usuario'),
            log.get('acao'),
            log.get('ip_origem')
        ])

    registrar_log("Exportou o relatorio de auditoria em CSV")
    resposta = make_response(saida.getvalue())
    resposta.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resposta.headers['Content-Disposition'] = 'attachment; filename=auditoria-jp2.csv'
    return resposta

@app.route('/listar')
def listar_arquivos():
    if 'usuario_logado' not in session: return jsonify({'erro': 'NÃ£o autorizado'}), 401
    bloco = request.args.get('bloco')
    pasta_pai_id = request.args.get('pasta_pai_id')
    cache_key = chave_listagem_cache(bloco, pasta_pai_id)
    cache_item = LISTAR_CACHE.get(cache_key)
    agora_cache = time.time()
    if cache_item and cache_item["expira_em"] > agora_cache:
        resp = make_response(jsonify(cache_item["dados"]))
        resp.headers['Cache-Control'] = 'private, max-age=12'
        resp.headers['X-Cache-Painel'] = 'HIT'
        return resp
    
    conn = None # Declaramos aqui para o finally poder acessar
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if pasta_pai_id and str(pasta_pai_id).strip() not in ["null", "undefined", ""]:
                cur.execute("""
                    SELECT id, nome_original, tipo, caminho_sistema, criado_por, bloco, categoria, pasta_pai_id
                    FROM arquivos_painel
                    WHERE bloco = %s AND pasta_pai_id = %s AND deletado = 0
                    ORDER BY tipo DESC, nome_original ASC
                """, (bloco, int(pasta_pai_id)))
            else:
                cur.execute("""
                    SELECT id, nome_original, tipo, caminho_sistema, criado_por, bloco, categoria, pasta_pai_id
                    FROM arquivos_painel
                    WHERE bloco = %s AND pasta_pai_id IS NULL AND deletado = 0
                    ORDER BY tipo DESC, nome_original ASC
                """, (bloco,))
            linhas = cur.fetchall()
        
        itens_formatados = []
        for l in linhas:
            itens_formatados.append(formatar_item_painel(l))
        
        payload = {'itens': itens_formatados}
        LISTAR_CACHE[cache_key] = {
            "expira_em": agora_cache + LISTAR_CACHE_TTL_SEGUNDOS,
            "dados": payload,
        }
        resp = make_response(jsonify(payload))
        resp.headers['Cache-Control'] = 'private, max-age=12'
        resp.headers['X-Cache-Painel'] = 'MISS'
        return resp

    except Exception as e:
        print(f"Erro ao listar: {e}")
        return jsonify({'itens': []})
    
    finally:
        if conn: conn.close() # Garantia absoluta de que a conexÃ£o fecharÃ¡
        
@app.route('/obter-pai-id')
def obter_pai_id():
    if 'usuario_logado' not in session: return jsonify({'pasta_pai_id': None}), 401
    bloco = request.args.get('bloco')
    caminho = request.args.get('caminho', '')
    partes = caminho.split(' / ')
    if len(partes) <= 1: return jsonify({'pasta_pai_id': None})
    ultima_pasta_nome = partes[-1]
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM arquivos_painel 
                WHERE bloco = %s AND nome_original = %s AND tipo = 'pasta' AND deletado = 0
                LIMIT 1
            """, (bloco, ultima_pasta_nome))
            dados = cur.fetchone()
        conn.close()
        return jsonify({'pasta_pai_id': dados['id'] if dados else None})
    except:
        return jsonify({'pasta_pai_id': None})

@app.route('/criar-pasta', methods=['POST'])
def criar_pasta():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    nome, bloco = request.form.get('nome'), request.form.get('bloco')
    cat = request.form.get('categoria') or 'raiz'
    pai = request.form.get('pasta_pai_id')
    p_id = int(pai) if (pai and str(pai).strip() not in ["null", "undefined", ""]) else None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO arquivos_painel (nome_original, bloco, categoria, tipo, pasta_pai_id, criado_por, deletado)
                VALUES (%s, %s, %s, 'pasta', %s, %s, 0)
            """, (nome, bloco, cat, p_id, session.get('nome_exibicao', 'Sistema')))
            novo_id = cur.lastrowid
        conn.commit()
        conn.close()
        invalidar_cache_listagem()
        registrar_log(f"Criou a pasta: {nome} no bloco {bloco}")
        return jsonify({
            'status': 'sucesso',
            'item': {
                'id': novo_id,
                'nome': nome,
                'tipo': 'pasta',
                'caminho': None,
                'imagem_bg': '',
                'autor': session.get('nome_exibicao', 'Sistema'),
                'bloco': bloco,
                'categoria': cat,
                'pasta_pai_id': p_id
            }
        })
    except Exception as e:
        print(f"Erro ao criar pasta: {e}")
        return jsonify({'status': 'erro', 'mensagem': 'Nao foi possivel criar a pasta.'}), 500

# ðŸš€ 1. INSTALAÃ‡ÃƒO DO MOTOR FATIADOR COMPATÃVEL COM ALTA VELOCIDADE (Mini-fatias)
@app.route('/upload-avancado', methods=['POST'])
def upload_avancado():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    
    file = request.files.get('arquivos')
    bloco = request.form.get('bloco')
    cat = request.form.get('categoria')
    pai = request.form.get('pasta_pai_id')
    p_id = int(pai) if (pai and str(pai).strip() not in ["null", "undefined", ""]) else None
    
    chunk_index = int(request.form.get('chunkIndex', 0))
    total_chunks = int(request.form.get('totalChunks', 1))
    guid_uuid = request.form.get('guid', uuid.uuid4().hex)
    nome_original = request.form.get('nome_original', file.filename if file else 'arquivo')
    
    conn = None
    try:
        nome_limpo = re.sub(r'[^a-zA-Z0-9._-]', '', nome_original.replace(' ', '_'))
        nome_unico = f"{guid_uuid}_{nome_limpo}"
        destino_completo = os.path.join(UPLOAD_FOLDER, nome_unico)
        
        if file:
            with open(destino_completo, 'ab') as f:
                f.write(file.read())
        
        if chunk_index + 1 == total_chunks:
            if not r2_configurado():
                return jsonify({
                    'status': 'erro',
                    'mensagem': 'Armazenamento R2 nao configurado no servidor.'
                }), 500

            chave_r2 = f"uploads/{bloco or 'geral'}/{nome_unico}"
            caminho_sistema = enviar_arquivo_r2(
                destino_completo,
                chave_r2,
                getattr(file, "content_type", None)
            )

            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO arquivos_painel (nome_original, caminho_sistema, bloco, categoria, tipo, criado_por, pasta_pai_id, deletado)
                    VALUES (%s, %s, %s, %s, 'arquivo', %s, %s, 0)
                """, (nome_original, caminho_sistema, bloco, cat, session.get('nome_exibicao', 'Sistema'), p_id))
                novo_id = cur.lastrowid

            try:
                os.remove(destino_completo)
            except OSError:
                pass

            invalidar_cache_resumo_dashboard()
            invalidar_cache_listagem()
            return jsonify({
                'status': 'sucesso',
                'guid': guid_uuid,
                'item': {
                    'id': novo_id,
                    'nome': nome_original,
                    'tipo': 'arquivo',
                    'caminho': caminho_sistema,
                    'imagem_bg': '',
                    'autor': session.get('nome_exibicao', 'Sistema'),
                    'bloco': bloco,
                    'categoria': cat,
                    'pasta_pai_id': p_id
                }
            })
            
        return jsonify({'status': 'sucesso', 'guid': guid_uuid})
    except Exception as e:
        print(f"ERRO NO UPLOAD FRAGMENTADO: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500
    finally:
        if conn: conn.close()
            
# ðŸŸ¢ 2. REMOÃ‡ÃƒO DE DUPLICIDADE: UNIFICAÃ‡ÃƒO DA ROTA INTELIGENTE DE VISUALIZAÃ‡ÃƒO E DOWNLOAD
@app.route('/baixar_recurso/<int:arquivo_id>')
def baixar_recurso_corporativo(arquivo_id):
    if 'usuario_logado' not in session: return "NÃ£o autorizado", 401
    force_download = request.args.get('download', 'false') == 'true'
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT caminho_sistema, nome_original, deletado FROM arquivos_painel WHERE id = %s", (arquivo_id,))
            dados = cur.fetchone()
        conn.close()
        
        if dados and dados['deletado'] != 1:
            caminho_sistema = dados.get('caminho_sistema') or ''
            if caminho_sistema.startswith('r2://'):
                registrar_log(f"Acessou o arquivo: {dados['nome_original']} (Download={force_download})")
                url_temporaria = gerar_url_temporaria_r2(
                    caminho_sistema,
                    dados['nome_original'],
                    force_download=force_download,
                    expires_in=300
                )
                if not force_download and arquivo_office(dados['nome_original']):
                    return redirect("https://view.officeapps.live.com/op/view.aspx?src=" + quote(url_temporaria, safe=""))
                return redirect(url_temporaria)

            nome_arquivo_fisico = dados['caminho_sistema'].split('/')[-1]
            arquivo_path = os.path.join(UPLOAD_FOLDER, nome_arquivo_fisico)
            
            if os.path.exists(arquivo_path):
                registrar_log(f"Acessou o arquivo: {dados['nome_original']} (Download={force_download})")
                # ðŸŸ¢ CORREÃ‡ÃƒO CIRÃšRGICA: caminho_absoluto com "o" no final
                return send_file(arquivo_path, download_name=dados['nome_original'], as_attachment=force_download)
            
    except Exception as e:
        print(f"ERRO DE FLUXO NO DOWNLOAD: {e}")
    return "Este arquivo fÃ­sico antigo foi removido pelo deploy temporÃ¡rio do servidor da Render. Por favor, exclua-o na lixeira e faÃ§a o upload novamente para registrar o link persistente rÃ¡pido.", 404

# ðŸ”’ 3. ROTA DE SEGURANÃ‡A PARA ALTERAÃ‡ÃƒO DE NOMES
@app.route('/renomear', methods=['POST'])
def renomear_item():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro', 'mensagem': 'NÃ£o autorizado'}), 401
    
    id_item = request.form.get('id')
    novo_nome = request.form.get('novo_nome', '').strip()
    senha = request.form.get('senha', '').strip()
    
    if not id_item or not novo_nome or not senha:
        return jsonify({'status': 'erro', 'mensagem': 'Preencha todos os campos obrigatÃ³rios!'}), 400
        
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT senha FROM usuarios WHERE usuario = %s", (session.get('usuario_logado'),))
            dados_u = cur.fetchone()
            user_senha = str(dados_u['senha']) if dados_u else ""
            
            if not senha_confere(user_senha, senha):
                conn.close()
                return jsonify({'status': 'erro', 'mensagem': 'Senha de validaÃ§Ã£o incorreta!'}), 401
            
            cur.execute("SELECT nome_original, tipo FROM arquivos_painel WHERE id = %s AND deletado = 0", (id_item,))
            item_antigo = cur.fetchone()
            
            if not item_antigo:
                conn.close()
                return jsonify({'status': 'erro', 'mensagem': 'Item nÃ£o localizado no servidor!'}), 404
                
            cur.execute("UPDATE arquivos_painel SET nome_original = %s WHERE id = %s", (novo_nome, id_item))
            
        conn.commit()
        conn.close()
        
        invalidar_cache_listagem()
        registrar_log(f"Renomeou o(a) {item_antigo['tipo']} '{item_antigo['nome_original']}' para '{novo_nome}' (ID: {id_item})")
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

@app.route('/excluir', methods=['POST'])
def excluir_arquivo():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    
    ids_enviados = request.form.get('id')
    senha = request.form.get('senha', '').strip()
    
    if not ids_enviados:
        return jsonify({'status': 'erro', 'mensagem': 'Nenhum item selecionado!'}), 400
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. ValidaÃ§Ã£o rÃ¡pida da senha
            cur.execute("SELECT senha FROM usuarios WHERE usuario = %s", (session.get('usuario_logado'),))
            dados_u = cur.fetchone()
            user_senha = str(dados_u['senha']) if dados_u else ""
            
            if senha_confere(user_senha, senha):
                lista_ids = [int(x.strip()) for x in str(ids_enviados).split(',') if x.strip().isdigit()]
                
                # 2. ExclusÃ£o direta
                format_strings = ','.join(['%s'] * len(lista_ids))
                cur.execute(f"""
                    UPDATE arquivos_painel 
                    SET deletado = 1, deletado_em = NOW() 
                    WHERE id IN ({format_strings}) AND deletado = 0
                """, tuple(lista_ids))

                invalidar_cache_resumo_dashboard()
                invalidar_cache_listagem()
                return jsonify({'status': 'sucesso'})
        
        return jsonify({'status': 'erro', 'mensagem': 'Senha incorreta!'})
    except Exception as e:
        print(f"ERRO NA EXCLUSÃƒO: {e}")
        return jsonify({'status': 'erro', 'mensagem': 'Erro interno'}), 500
    finally:
        if conn: conn.close() # Garantia que a conexÃ£o sempre fecha
        
@app.route('/salvar-site', methods=['POST'])
def salvar_site():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    nome, url, bloco = request.form.get('nome'), request.form.get('url'), request.form.get('bloco')
    categoria_site = request.form.get('categoria_site', 'operacao')
    if categoria_site not in ['institucional', 'eventos', 'marcas', 'operacao']:
        categoria_site = 'operacao'
    
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url

    if not bloco or str(bloco).strip().lower() in ["", "null", "undefined", "sites jp2 business"]:
        bloco_final = 'sites_jp2'
    else:
        bloco_final = str(bloco).strip()

    logo_capturada = capturar_logo_site(nome, url)
    if logo_capturada:
        print(f"Logo capturada para {nome}: {logo_capturada}", flush=True)
    else:
        print(f"Nao foi possivel capturar logo para {nome}; card usara fallback.", flush=True)

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO arquivos_painel (nome_original, bloco, tipo, categoria, caminho_sistema, criado_por, deletado)
                VALUES (%s, %s, 'link', %s, %s, %s, 0)
            """, (nome, bloco_final, categoria_site, url, session.get('nome_exibicao', 'Sistema')))
        conn.commit()
        conn.close()
        invalidar_cache_listagem()
        registrar_log(f"Incluiu o site {nome} ({url}) na categoria {categoria_site}")
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        print(f"Erro ao salvar site: {e}")
        return jsonify({'status': 'erro', 'mensagem': 'Nao foi possivel salvar o site.'}), 500
        
@app.route('/api/listar-eventos')
def api_listar_eventos():
    try:
        garantir_colunas_agenda()
        data_inicio = data_iso_ou_none(request.args.get('start'))
        data_fim = data_iso_ou_none(request.args.get('end'))
        conn = get_db_connection()
        with conn.cursor() as cur:
            if data_inicio and data_fim:
                cur.execute("""
                    SELECT id, titulo, data_evento, data_fim, tipo_evento, local_evento, horario
                    FROM agenda_eventos
                    WHERE data_evento <= %s
                      AND COALESCE(data_fim, data_evento) >= %s
                    ORDER BY data_evento ASC
                """, (data_fim, data_inicio))
            else:
                cur.execute("""
                    SELECT id, titulo, data_evento, data_fim, tipo_evento, local_evento, horario
                    FROM agenda_eventos
                    WHERE data_evento >= %s
                    ORDER BY data_evento ASC
                    LIMIT 500
                """, ((datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),))
            eventos = cur.fetchall()
        conn.close()
        
        lista_diaria = []
        for ev in eventos:
            titulo, inicio_str, fim_str = ev['titulo'], str(ev['data_evento']), str(ev['data_fim'] or ev['data_evento'])
            tipo = ev.get('tipo_evento') or 'reuniao'
            cor = '#155eef' if tipo == 'reuniao' else '#078c55'
            horario = ev.get('horario') or ''
            local = ev.get('local_evento') or ''
            titulo_calendario = f"{horario} - {titulo}" if horario and tipo == 'reuniao' else titulo
            try:
                inicio = datetime.strptime(inicio_str[:10], '%Y-%m-%d')
                fim = datetime.strptime(fim_str[:10], '%Y-%m-%d')
                for i in range((fim - inicio).days + 1):
                    lista_diaria.append({
                        'id': ev.get('id'),
                        'title': titulo_calendario,
                        'start': (inicio + timedelta(days=i)).strftime('%Y-%m-%d'), 
                        'allDay': True, 
                        'color': cor,
                        'extendedProps': {
                            'tipo': tipo,
                            'local': local,
                            'horario': horario,
                            'titulo_original': titulo
                        }
                    })
            except: continue
        resp = make_response(jsonify(lista_diaria))
        resp.headers['Cache-Control'] = 'private, max-age=20'
        return resp
    except: return jsonify([])

@app.route('/adicionar-evento', methods=['POST'])
def calendar_adicionar():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    tipo = request.form.get('tipo_evento', 'reuniao')
    titulo = request.form.get('titulo', '').strip()
    local = request.form.get('local_evento', '').strip()
    horario = request.form.get('horario', '').strip()
    data_ini = request.form.get('dataReuniaoInput')
    data_fim = request.form.get('data_fim') or data_ini
    if tipo not in ['reuniao', 'evento']:
        tipo = 'reuniao'
    if not titulo: return {"status": "erro", "mensagem": "Informe o titulo do compromisso."}, 400
    if not data_ini: return {"status": "erro", "mensagem": "Data nao enviada."}, 400
    if tipo == 'evento' and data_fim and data_fim < data_ini:
        return {"status": "erro", "mensagem": "A data final nao pode ser anterior a data inicial."}, 400
    try:
        garantir_colunas_agenda()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO agenda_eventos (titulo, data_evento, data_fim, tipo_evento, local_evento, horario, criado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (titulo, data_ini, data_fim, tipo, local, horario, session.get('nome_exibicao', 'Sistema')))
        conn.commit()
        conn.close()
        invalidar_cache_resumo_dashboard()
        registrar_log(f"Adicionou um compromisso na agenda: {titulo}")
        return {"status": "sucesso"}, 200
    except Exception as e: return {"status": "erro", "mensagem": str(e)}, 500

@app.route('/excluir-evento', methods=['POST'])
def excluir_evento():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    evento_id = request.form.get('id')
    titulo = request.form.get('titulo', '').strip()
    senha = request.form.get('senha', '').strip()
    if not senha:
        return jsonify({'status': 'erro', 'mensagem': 'Informe sua senha para excluir.'}), 400
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT senha FROM usuarios WHERE usuario = %s", (session.get('usuario_logado'),))
            dados_u = cur.fetchone()
            user_senha = str(dados_u['senha']) if dados_u else ""
            
            if not senha_confere(user_senha, senha):
                conn.close()
                return jsonify({'status': 'erro', 'mensagem': 'Senha incorreta.'}), 401

            if evento_id and evento_id != "" and evento_id != "undefined" and evento_id != "null":
                cur.execute("DELETE FROM agenda_eventos WHERE id = %s", (int(evento_id),))
                registrar_log(f"Apagou o compromisso da agenda ID: {evento_id}")
            elif titulo:
                cur.execute("DELETE FROM agenda_eventos WHERE titulo LIKE %s", (titulo,))
                registrar_log(f"Apagou o compromisso da agenda por titulo: {titulo}")
            else:
                conn.close()
                return jsonify({'status': 'erro', 'mensagem': 'Compromisso nao identificado.'}), 400
        conn.commit()
        conn.close()
        invalidar_cache_resumo_dashboard()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        print(f"Erro ao excluir compromisso: {e}")
        return jsonify({'status': 'erro', 'mensagem': 'Erro interno ao excluir compromisso.'}), 500

@app.route('/api/resumo-dashboard')
def resumo_dashboard():
    try:
        agora = datetime.now()
        if RESUMO_DASHBOARD_CACHE["dados"] and RESUMO_DASHBOARD_CACHE["expira_em"] and RESUMO_DASHBOARD_CACHE["expira_em"] > agora:
            resp = make_response(jsonify(RESUMO_DASHBOARD_CACHE["dados"]))
            resp.headers['Cache-Control'] = 'private, max-age=30'
            return resp

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(id) as total FROM arquivos_painel WHERE tipo = 'arquivo' AND deletado = 0")
            total_arquivos = cur.fetchone()['total']
            cur.execute("SELECT COUNT(id) as total FROM usuarios")
            total_socios = cur.fetchone()['total']
            hoje = datetime.now().strftime('%Y-%m-%d')
            cur.execute("SELECT titulo FROM agenda_eventos WHERE data_evento >= %s ORDER BY data_evento ASC LIMIT 1", (hoje,))
            dados_ev = cur.fetchone()
            proximo_evento = dados_ev['titulo'] if dados_ev else "Nenhum"
        conn.close()
        dados_resumo = {
            'total_arquivos': total_arquivos,
            'total_socios': total_socios,
            'proximo_evento': proximo_evento
        }
        RESUMO_DASHBOARD_CACHE["dados"] = dados_resumo
        RESUMO_DASHBOARD_CACHE["expira_em"] = agora + timedelta(seconds=30)
        resp = make_response(jsonify(dados_resumo))
        resp.headers['Cache-Control'] = 'private, max-age=30'
        return resp
    except: return jsonify({'error': 'erro'}), 500

@app.route('/api/performance-status')
def performance_status():
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro'}), 401

    recentes = list(PERFORMANCE_ROTAS)[-12:]
    return jsonify({
        'status': 'sucesso',
        'total_amostras': len(PERFORMANCE_ROTAS),
        'resumo': resumo_performance_rotas()[:6],
        'recentes': recentes[::-1]
    })

@app.route('/manifest.json')
def manifest(): return send_from_directory('static', 'manifest.json')    

if __name__ == '__main__':
    app.run(debug=True)



