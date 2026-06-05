import os
import uuid
import re
import tempfile
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, make_response, send_from_directory
from supabase import create_client
from datetime import datetime, timedelta

# CONFIGURAÇÃO DE INFRAESTRUTURA SEGURA
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://zkdzgpblxorcxxdrmojo.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not SUPABASE_KEY:
    raise ValueError("ERRO CRÍTICO: A chave SUPABASE_KEY não foi configurada nas Variáveis de Ambiente da Render!")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_secreta_super_segura_jp2")

# Conexão direta com o banco Neon (PostgreSQL)
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def registrar_log(acao):
    try:
        usuario = session.get('nome_exibicao', 'Sistema / Desconhecido')
        ip_usuario = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO logs_auditoria (usuario, acao, ip_origem)
            VALUES (%s, %s, %s)
        """, (usuario, acao, ip_usuario))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"ERRO AO REGISTRAR LOG: {e}")

def criptografar_sha256(senha_pura):
    return hashlib.sha256(senha_pura.encode('utf-8')).hexdigest()

@app.route('/login', methods=['GET', 'POST'])
def tela_login():
    if request.method == 'POST':
        u = request.form.get('usuario', '').lower().strip()
        s = request.form.get('senha', '').strip()
        
        # ACESSO MESTRE TEMPORÁRIO PARA O SEU CONTROLE
        if u == 'petrick':
            session['usuario_logado'] = 'petrick'
            session['nome_exibicao'] = 'Petrick Martins'
            registrar_log("Realizou login via mestre temporário")
            return redirect(url_for('home'))
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM usuarios WHERE usuario = %s", (u,))
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            if user:
                if str(user['senha']) == criptografar_sha256(s):
                    session['usuario_logado'] = user['usuario']
                    session['nome_exibicao'] = user.get('nome_exibicao', user['usuario'])
                    registrar_log("Realizou login no sistema")
                    return redirect(url_for('home'))
                else:
                    flash("Senha incorreta digitada!")
            else:
                flash("Usuário não encontrado no sistema!")
        except Exception as e:
            print(f"Erro no Login: {e}")
            flash(f"Erro de conexão com o banco: {str(e)}")
            return redirect(url_for('tela_login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    registrar_log("Realizou logout no sistema")
    session.clear()
    return redirect(url_for('tela_login'))

@app.route('/')
def home():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    return render_template('home.html', nome_sócio=session.get('nome_exibicao', 'Sócio'))

@app.route('/agenda')
def pagina_agenda():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    return render_template('agenda.html', nome_sócio=session.get('nome_exibicao', 'Sócio'))

@app.route('/admin/usuarios', methods=['GET', 'POST'])
def admin_usuarios():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    
    if request.method == 'POST':
        novo_user = request.form.get('novo_usuario', '').lower().strip()
        senha_pura = request.form.get('nova_senha', '').strip()
        nome_exib = request.form.get('nome_exibicao', '')
        senha_cripto = criptografar_sha256(senha_pura)
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO usuarios (usuario, senha, nome_exibicao)
                VALUES (%s, %s, %s)
            """, (novo_user, senha_cripto, nome_exib))
            conn.commit()
            cur.close()
            conn.close()
            registrar_log(f"Cadastrou um novo usuário no painel: {novo_user}")
        except Exception as e:
            print(f"Erro cadastro: {e}")
            
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, usuario, nome_exibicao FROM usuarios")
    lista_usuarios = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_usuarios.html', usuarios=lista_usuarios)

@app.route('/admin/excluir_usuario/<int:usuario_id>', methods=['POST'])
def excluir_usuario(usuario_id):
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conn.commit()
        cur.close()
        conn.close()
        registrar_log(f"Removeu o usuário ID: {usuario_id} do sistema")
        flash("Sócio removido com sucesso!")
    except Exception as e:
        print(f"Erro ao deletar usuário: {e}")
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/logs')
def admin_logs():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM logs_auditoria ORDER BY data_registro DESC LIMIT 100")
        lista_logs = cur.fetchall()
        cur.close()
        conn.close()
    except:
        lista_logs = []
    return render_template('admin_logs.html', logs=lista_logs)

@app.route('/listar')
def listar_arquivos():
    if 'usuario_logado' not in session: return jsonify({'erro': 'Não autorizado'}), 401
    bloco = request.args.get('bloco')
    pasta_pai_id = request.args.get('pasta_pai_id')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # SOLUÇÃO MÁGICA: Se o front-end chamar por sites_jp2 OU se perder no console tentando renderizar, traz os links de uma vez só
        if bloco == 'sites_jp2' or bloco == 'instituto':
            cur.execute("""
                SELECT * FROM arquivos_painel 
                WHERE (bloco = 'sites_jp2' OR bloco = 'instituto') AND tipo = 'link' AND (deletado = False OR deletado IS NULL)
            """)
        else:
            if pasta_pai_id and str(pasta_pai_id).strip() not in ["null", "undefined", ""]:
                cur.execute("""
                    SELECT * FROM arquivos_painel 
                    WHERE bloco = %s AND (deletado = False OR deletado IS NULL) AND pasta_pai_id = %s
                """, (bloco, int(pasta_pai_id)))
            else:
                cur.execute("""
                    SELECT * FROM arquivos_painel 
                    WHERE bloco = %s AND (deletado = False OR deletado IS NULL) AND pasta_pai_id IS NULL
                """, (bloco,))
            
        linhas = cur.fetchall()
        cur.close()
        conn.close()
        
        itens_formatados = []
        for l in linhas:
            itens_formatados.append({
                'id': l['id'], 'nome': l['nome_original'], 'tipo': l['tipo'], 
                'caminho': l['caminho_sistema'], 'autor': l['criado_por'] or 'Sistema', 
                'bloco': l['bloco'], 'categoria': l['categoria'], 'pasta_pai_id': l['pasta_pai_id']
            })
        return jsonify({'itens': itens_formatados})
    except Exception as e:
        print(f"Erro ao listar: {e}")
        return jsonify({'itens': []})

@app.route('/obter-pai-id')
def obter_pai_id():
    if 'usuario_logado' not in session: return jsonify({'pasta_pai_id': None}), 401
    bloco = request.args.get('bloco')
    caminho = request.args.get('caminho', '')
    partes = caminho.split(' ➔ ')
    if len(partes) <= 1: return jsonify({'pasta_pai_id': None})
    ultima_pasta_nome = partes[-1]
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM arquivos_painel 
            WHERE bloco = %s AND nome_original = %s AND tipo = 'pasta' AND (deletado = False OR deletado IS NULL)
            LIMIT 1
        """, (bloco, ultima_pasta_nome))
        dados = cur.fetchone()
        cur.close()
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
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO arquivos_painel (nome_original, bloco, categoria, tipo, pasta_pai_id, criado_por, deletado)
            VALUES (%s, %s, %s, %s, %s, %s, False)
        """, (nome, bloco, cat, 'pasta', p_id, session.get('nome_exibicao', 'Sistema')))
        conn.commit()
        cur.close()
        conn.close()
        registrar_log(f"Criou a pasta: {nome} no bloco {bloco}")
        return jsonify({'status': 'sucesso'})
    except:
        return jsonify({'status': 'erro'})

@app.route('/upload-avancado', methods=['POST'])
def upload_avancado():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    arquivos = request.files.getlist('arquivos')
    bloco, cat, pai = request.form.get('bloco'), request.form.get('categoria'), request.form.get('pasta_pai_id')
    p_id = int(pai) if (pai and str(pai).strip() not in ["null", "undefined", ""]) else None
    
    try:
        for arq in arquivos:
            if arq.filename == '': continue
            
            nome_limpo = re.sub(r'[^a-zA-Z0-9._-]', '', arq.filename.replace(' ', '_'))
            nome_unico = f"{uuid.uuid4().hex}_{nome_limpo}"
            
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                arq.save(tmp.name)
                tmp_path = tmp.name

            with open(tmp_path, 'rb') as f:
                supabase.storage.from_("meus-arquivos").upload(
                    path=nome_unico, 
                    file=f, 
                    file_options={"content-type": arq.content_type}
                )
            
            os.remove(tmp_path)
            link = supabase.storage.from_("meus-arquivos").get_public_url(nome_unico)
            
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO arquivos_painel (nome_original, caminho_sistema, bloco, categoria, tipo, criado_por, pasta_pai_id, deletado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, False)
            """, (arq.filename, link, bloco, cat, 'arquivo', session.get('nome_exibicao', 'Sistema'), p_id))
            conn.commit()
            cur.close()
            conn.close()
            
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        print(f"ERRO CRÍTICO NO UPLOAD: {e}")
        if 'tmp_path' in locals() and os.path.exists(tmp_path): os.remove(tmp_path)
        return jsonify({'status': 'erro', 'mensagem': str(e)})
        
@app.route('/baixar/<int:arquivo_id>')
def baixar_arquivo(arquivo_id):
    if 'usuario_logado' not in session: return "Não autorizado", 401
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT caminho_sistema, nome_original, deletado FROM arquivos_painel WHERE id = %s", (arquivo_id,))
        dados = cur.fetchone()
        cur.close()
        conn.close()
        
        if dados and dados['deletado'] != True:
            registrar_log(f"Fez download do arquivo: {dados['nome_original']}")
            if dados['caminho_sistema'].startswith('http'): 
                return redirect(dados['caminho_sistema'])
    except: pass
    return "Arquivo não encontrado", 404

@app.route('/excluir', methods=['POST'])
def excluir_arquivo():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    arq_id, senha = request.form.get('id'), request.form.get('senha', '').strip()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT senha FROM usuarios WHERE usuario = %s", (session.get('usuario_logado'),))
        dados_u = cur.fetchone()
        user_senha = str(dados_u['senha']) if dados_u else ""
        
        if user_senha == criptografar_sha256(senha):
            cur.execute("SELECT nome_original FROM arquivos_painel WHERE id = %s", (arq_id,))
            res_arq = cur.fetchone()
            nome_arq = res_arq['nome_original'] if res_arq else "Desconhecido"
            
            cur.execute("""
                UPDATE arquivos_painel 
                SET deletado = True, deletado_em = %s 
                WHERE id = %s
            """, (datetime.now().isoformat(), arq_id))
            conn.commit()
            cur.close()
            conn.close()
            
            registrar_log(f"Enviou para a lixeira o item/pasta: {nome_arq} (ID: {arq_id})")
            return jsonify({'status': 'sucesso'})
        
        cur.close()
        conn.close()
        return jsonify({'status': 'erro', 'mensagem': 'Senha incorreta!'})
    except:
        return jsonify({'status': 'erro'})

@app.route('/salvar-site', methods=['POST'])
def salvar_site():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    nome, url, bloco = request.form.get('nome'), request.form.get('url'), request.form.get('bloco')
    
    bloco_final = bloco or 'sites_jp2'
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO arquivos_painel (nome_original, bloco, tipo, categoria, caminho_sistema, criado_por, deletado)
            VALUES (%s, %s, %s, %s, %s, %s, False)
        """, (nome, bloco_final, 'link', 'sites_jp2', url, session.get('nome_exibicao', 'Sistema')))
        conn.commit()
        cur.close()
        conn.close()
        registrar_log(f"Incluiu o site institucional: {nome} ({url})")
        return jsonify({'status': 'sucesso'})
    except:
        return jsonify({'status': 'erro'})

@app.route('/api/listar-eventos')
def api_listar_eventos():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, titulo, data_evento, data_fim FROM agenda_eventos")
        eventos = cur.fetchall()
        cur.close()
        conn.close()
        
        lista_diaria = []
        for ev in eventos:
            titulo, inicio_str, fim_str = ev['titulo'], str(ev['data_evento']), str(ev['data_fim'] or ev['data_evento'])
            cor = '#dc2626' if "reuniao" in titulo.lower() else ('#7c3aed' if "evento" in titulo.lower() else '#3b82f6')
            try:
                inicio = datetime.strptime(inicio_str[:10], '%Y-%m-%d')
                fim = datetime.strptime(fim_str[:10], '%Y-%m-%d')
                for i in range((fim - inicio).days + 1):
                    lista_diaria.append({
                        'id': ev.get('id'),
                        'title': titulo, 
                        'start': (inicio + timedelta(days=i)).strftime('%Y-%m-%d'), 
                        'allDay': True, 
                        'color': cor
                    })
            except: continue
        resp = make_response(jsonify(lista_diaria))
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
    except: return jsonify([])

@app.route('/adicionar-evento', methods=['POST'])
def calendar_adicionar():
    titulo, data_ini = request.form.get('titulo'), request.form.get('dataReuniaoInput')
    data_fim = request.form.get('data_fim') or data_ini
    if not data_ini: return {"status": "erro", "mensagem": "Data não enviada!"}, 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO agenda_eventos (titulo, data_evento, data_fim)
            VALUES (%s, %s, %s)
        """, (titulo, data_ini, data_fim))
        conn.commit()
        cur.close()
        conn.close()
        registrar_log(f"Adicionou um compromisso na agenda: {titulo}")
        return {"status": "sucesso"}, 200
    except Exception as e: return {"status": "erro", "mensagem": str(e)}, 500

@app.route('/excluir-evento', methods=['POST'])
def excluir_evento():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    evento_id = request.form.get('id')
    titulo = request.form.get('titulo', '').strip()
    senha = request.form.get('senha', '').strip()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT senha FROM usuarios WHERE usuario = %s", (session.get('usuario_logado'),))
        dados_u = cur.fetchone()
        user_senha = str(dados_u['senha']) if dados_u else ""
        
        if user_senha == criptografar_sha256(senha):
            if evento_id and evento_id != "" and evento_id != "undefined" and evento_id != "null":
                cur.execute("DELETE FROM agenda_eventos WHERE id = %s", (int(evento_id),))
                registrar_log(f"Apagou o compromisso da agenda ID: {evento_id}")
            elif titulo:
                cur.execute("DELETE FROM agenda_eventos WHERE titulo ILIKE %s", (titulo,))
                registrar_log(f"Apagou o compromisso da agenda por título: {titulo}")
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'status': 'sucesso'})
        cur.close()
        conn.close()
        return jsonify({'status': 'erro', 'mensagem': 'Senha incorreta!'})
    except: return jsonify({'status': 'erro'})

@app.route('/api/resumo-dashboard')
def resumo_dashboard():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(id) as total FROM arquivos_painel WHERE (deletado = False OR deletado IS NULL) AND tipo = 'arquivo'")
        total_arquivos = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(id) as total FROM usuarios")
        total_socios = cur.fetchone()['total']
        
        hoje = datetime.now().strftime('%Y-%m-%d')
        cur.execute("SELECT titulo FROM agenda_eventos WHERE data_evento >= %s ORDER BY data_evento ASC LIMIT 1", (hoje,))
        dados_ev = cur.fetchone()
        proximo_evento = dados_ev['titulo'] if dados_ev else "Nenhum"
        
        cur.close()
        conn.close()
        return jsonify({'total_arquivos': total_arquivos, 'total_socios': total_socios, 'proximo_evento': proximo_evento})
    except: return jsonify({'error': 'erro'}), 500

@app.route('/manifest.json')
def manifest(): return send_from_directory('static', 'manifest.json')    

if __name__ == '__main__':
    app.run(debug=True)
