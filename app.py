import os
import uuid
import re
import hashlib
import traceback
import urllib.request
import csv
import io
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin, urlparse
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, make_response, send_from_directory, send_file
from database import get_db_connection
from storage import enviar_arquivo_r2, gerar_url_temporaria_r2, r2_configurado
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# ConfiguraÃ§Ãµes iniciais
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Defina a variavel FLASK_SECRET_KEY antes de iniciar o painel.")
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
INDICES_PERFORMANCE_VERIFICADOS = False
COLUNA_PERFIL_USUARIOS_VERIFICADA = False
COLUNAS_AGENDA_VERIFICADAS = False
USUARIOS_ADMIN_CACHE = None
RESUMO_DASHBOARD_CACHE = {"expira_em": None, "dados": None}

# Registro do mÃ³dulo financeiro
from financeiro import bp_financeiro
app.register_blueprint(bp_financeiro)

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

def data_iso_ou_none(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None

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

def nome_base_imagem_site(nome):
    return "".join(x for x in str(nome or "") if x.isalnum())

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
    
    # Debug: Printa o caminho real onde o Flask busca o 'home.html'
    template_path = os.path.join(app.root_path, 'templates', 'home.html')
    print("DEBUG: O Flask estÃ¡ buscando o arquivo em ->", template_path)
    
    return render_template('home.html', nome_socio=session.get('nome_exibicao', 'Socio'))

@app.route('/login', methods=['GET', 'POST'])
def tela_login():
    if request.method == 'POST':
        u = request.form.get('usuario', '').lower().strip()
        s = request.form.get('senha', '').strip()

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

                    session['usuario_logado'] = user['usuario']
                    session['nome_exibicao'] = user.get('nome_exibicao', user['usuario'])
                    session['perfil_usuario'] = user.get('perfil') or obter_perfil_usuario(user['usuario']) or 'socio'
                    registrar_log("Realizou login no sistema")
                    return redirect(url_for('home'))

                if user:
                    flash("Senha incorreta digitada!")
                else:
                    flash("Usuario nao encontrado no sistema!")
        except Exception as e:
            print(f"Erro no Login: {e}")
            flash(f"Erro de conexao com o banco: {str(e)}")
            return redirect(url_for('tela_login'))
        finally:
            if conn:
                conn.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    registrar_log("Realizou logout no sistema")
    session.clear()
    return redirect(url_for('tela_login'))

@app.route('/agenda')
def pagina_agenda():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    return render_template('agenda.html', nome_socio=session.get('nome_exibicao', 'Socio'))

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
            registrar_log(f"Cadastrou um novo usuÃ¡rio no painel: {novo_user}")
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
                flash("Voce nao pode excluir seu proprio usuario.")
                conn.close()
                return redirect(url_for('admin_usuarios'))
            cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conn.commit()
        conn.close()
        invalidar_cache_resumo_dashboard()
        registrar_log(f"Removeu o usuÃ¡rio ID: {usuario_id} do sistema")
        flash("SÃ³cio removido com sucesso!")
    except Exception as e:
        print(f"Erro ao deletar usuÃ¡rio: {e}")
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/alterar_perfil/<int:usuario_id>', methods=['POST'])
def alterar_perfil_usuario(usuario_id):
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    if not usuario_atual_e_admin():
        return acesso_negado()

    novo_perfil = request.form.get('perfil', 'socio')
    if novo_perfil not in ['admin', 'socio', 'leitura']:
        flash("Perfil invalido.")
        return redirect(url_for('admin_usuarios'))

    try:
        garantir_coluna_perfil_usuarios()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT usuario, perfil FROM usuarios WHERE id = %s", (usuario_id,))
            usuario_alvo = cur.fetchone()
            if not usuario_alvo:
                flash("Usuario nao encontrado.")
                conn.close()
                return redirect(url_for('admin_usuarios'))

            if usuario_alvo.get('usuario') == session.get('usuario_logado') and novo_perfil != 'admin':
                flash("Voce nao pode remover seu proprio perfil de administrador.")
                conn.close()
                return redirect(url_for('admin_usuarios'))

            cur.execute("UPDATE usuarios SET perfil = %s WHERE id = %s", (novo_perfil, usuario_id))
        conn.close()
        registrar_log(f"Alterou perfil do usuario {usuario_alvo.get('usuario')} para {novo_perfil}")
        flash("Perfil atualizado com sucesso.")
    except Exception as e:
        print(f"Erro ao alterar perfil: {e}")
        flash("Nao foi possivel atualizar o perfil.")

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
        flash("A confirmacao da senha nao confere.")
        return redirect(url_for('admin_usuarios'))

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT usuario FROM usuarios WHERE id = %s", (usuario_id,))
            usuario_alvo = cur.fetchone()
            if not usuario_alvo:
                flash("Usuario nao encontrado.")
                conn.close()
                return redirect(url_for('admin_usuarios'))

            cur.execute(
                "UPDATE usuarios SET senha = %s WHERE id = %s",
                (gerar_hash_senha(nova_senha), usuario_id)
            )
        conn.close()
        registrar_log(f"Alterou a senha do usuario {usuario_alvo.get('usuario')}")
        flash("Senha atualizada com sucesso.")
    except Exception as e:
        print(f"Erro ao alterar senha: {e}")
        flash("Nao foi possivel alterar a senha.")

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
        
        resp = make_response(jsonify({'itens': itens_formatados}))
        resp.headers['Cache-Control'] = 'private, max-age=30'
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

@app.route('/manifest.json')
def manifest(): return send_from_directory('static', 'manifest.json')    

if __name__ == '__main__':
    app.run(debug=True)



