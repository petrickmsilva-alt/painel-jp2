import os
import uuid
import re
import tempfile
import hashlib
import pymysql
import urllib.request
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, make_response, send_from_directory, send_file

app = Flask(__name__)
# Configura o limite de tráfego do Flask para arquivos grandes direto na HostGator
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_secreta_super_segura_jp2")

# DIRETÓRIO LOCAL DE ARMAZENAMENTO (Dentro da estrutura da HostGator)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Conexão otimizada com autocommit para maior velocidade e estabilidade
def get_db_connection():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

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

@app.route('/login', methods=['GET', 'POST'])
def tela_login():
    if request.method == 'POST':
        u = request.form.get('usuario', '').lower().strip()
        s = request.form.get('senha', '').strip()
        
        # ACESSO MESTRE TEMPORÁRIO PARA O SEU PRIMEIRO ACESSO LOCAL
        if u == 'petrick':
            session['usuario_logado'] = 'petrick'
            session['nome_exibicao'] = 'Petrick Martins'
            registrar_log("Realizou login via mestre temporário")
            return redirect(url_for('home'))
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM usuarios WHERE usuario = %s", (u,))
                user = cur.fetchone()
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
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usuarios (usuario, senha, nome_exibicao)
                    VALUES (%s, %s, %s)
                """, (novo_user, senha_cripto, nome_exib))
            conn.commit()
            conn.close()
            registrar_log(f"Cadastrou um novo usuário no painel: {novo_user}")
        except Exception as e:
            print(f"Erro cadastro: {e}")
            
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, usuario, nome_exibicao FROM usuarios")
        lista_usuarios = cur.fetchall()
    conn.close()
    return render_template('admin_usuarios.html', usuarios=lista_usuarios)

@app.route('/admin/excluir_usuario/<int:usuario_id>', methods=['POST'])
def excluir_usuario(usuario_id):
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conn.commit()
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
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM logs_auditoria ORDER BY data_registro DESC LIMIT 100")
            lista_logs = cur.fetchall()
        conn.close()
    except:
        lista_logs = []
    return render_template('admin_logs.html', logs=lista_logs)

@app.route('/listar')
def listar_arquivos():
    if 'usuario_logado' not in session: return jsonify({'erro': 'Não autorizado'}), 401
    bloco = request.args.get('bloco')
    pasta_pai_id = request.args.get('pasta_pai_id')
    
    conn = None # Declaramos aqui para o finally poder acessar
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if pasta_pai_id and str(pasta_pai_id).strip() not in ["null", "undefined", ""]:
                cur.execute("SELECT * FROM arquivos_painel WHERE bloco = %s AND pasta_pai_id = %s AND deletado = 0", (bloco, int(pasta_pai_id)))
            else:
                cur.execute("SELECT * FROM arquivos_painel WHERE bloco = %s AND pasta_pai_id IS NULL AND deletado = 0", (bloco,))
            linhas = cur.fetchall()
        
        itens_formatados = []
        for l in linhas:
            nome_limpo = "".join(x for x in l.get('nome_original', '') if x.isalnum())
            itens_formatados.append({
                'id': l['id'], 'nome': l['nome_original'], 'tipo': l['tipo'], 
                'caminho': l['caminho_sistema'], 'imagem_bg': f"/static/image/{nome_limpo}.jpeg",
                'autor': l['criado_por'] or 'Sistema', 'bloco': l['bloco'], 
                'categoria': l['categoria'], 'pasta_pai_id': l['pasta_pai_id']
            })
        
        resp = make_response(jsonify({'itens': itens_formatados}))
        resp.headers['Cache-Control'] = 'public, max-age=300'
        return resp

    except Exception as e:
        print(f"Erro ao listar: {e}")
        return jsonify({'itens': []})
    
    finally:
        if conn: conn.close() # Garantia absoluta de que a conexão fechará
        
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
        conn.commit()
        conn.close()
        registrar_log(f"Criou a pasta: {nome} no bloco {bloco}")
        return jsonify({'status': 'sucesso'})
    except:
        return jsonify({'status': 'erro'})

# 🚀 1. INSTALAÇÃO DO MOTOR FATIADOR COMPATÍVEL COM ALTA VELOCIDADE (Mini-fatias)
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
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO arquivos_painel (nome_original, caminho_sistema, bloco, categoria, tipo, criado_por, pasta_pai_id, deletado)
                    VALUES (%s, %s, %s, %s, 'arquivo', %s, %s, 0)
                """, (nome_original, f"/static/uploads/{nome_unico}", bloco, cat, session.get('nome_exibicao', 'Sistema'), p_id))
            
        return jsonify({'status': 'sucesso', 'guid': guid_uuid})
    except Exception as e:
        print(f"ERRO NO UPLOAD FRAGMENTADO: {e}")
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500
    finally:
        if conn: conn.close()
            
# 🟢 2. REMOÇÃO DE DUPLICIDADE: UNIFICAÇÃO DA ROTA INTELIGENTE DE VISUALIZAÇÃO E DOWNLOAD
@app.route('/baixar_recurso/<int:arquivo_id>')
def baixar_recurso_corporativo(arquivo_id):
    if 'usuario_logado' not in session: return "Não autorizado", 401
    force_download = request.args.get('download', 'false') == 'true'
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT caminho_sistema, nome_original, deletado FROM arquivos_painel WHERE id = %s", (arquivo_id,))
            dados = cur.fetchone()
        conn.close()
        
        if dados and dados['deletado'] != 1:
            nome_arquivo_fisico = dados['caminho_sistema'].split('/')[-1]
            arquivo_path = os.path.join(UPLOAD_FOLDER, nome_arquivo_fisico)
            
            if os.path.exists(arquivo_path):
                registrar_log(f"Acessou o arquivo: {dados['nome_original']} (Download={force_download})")
                # 🟢 CORREÇÃO CIRÚRGICA: caminho_absoluto com "o" no final
                return send_file(arquivo_path, download_name=dados['nome_original'], as_attachment=force_download)
            
    except Exception as e:
        print(f"ERRO DE FLUXO NO DOWNLOAD: {e}")
    return "Este arquivo físico antigo foi removido pelo deploy temporário do servidor da Render. Por favor, exclua-o na lixeira e faça o upload novamente para registrar o link persistente rápido.", 404

# 🔒 3. ROTA DE SEGURANÇA PARA ALTERAÇÃO DE NOMES
@app.route('/renomear', methods=['POST'])
def renomear_item():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro', 'mensagem': 'Não autorizado'}), 401
    
    id_item = request.form.get('id')
    novo_nome = request.form.get('novo_nome', '').strip()
    senha = request.form.get('senha', '').strip()
    
    if not id_item or not novo_nome or not senha:
        return jsonify({'status': 'erro', 'mensagem': 'Preencha todos os campos obrigatórios!'}), 400
        
    senha_hash = criptografar_sha256(senha)
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT senha FROM usuarios WHERE usuario = %s", (session.get('usuario_logado'),))
            dados_u = cur.fetchone()
            user_senha = str(dados_u['senha']) if dados_u else ""
            
            if user_senha != senha_hash:
                conn.close()
                return jsonify({'status': 'erro', 'mensagem': 'Senha de validação incorreta!'}), 401
            
            cur.execute("SELECT nome_original, tipo FROM arquivos_painel WHERE id = %s AND deletado = 0", (id_item,))
            item_antigo = cur.fetchone()
            
            if not item_antigo:
                conn.close()
                return jsonify({'status': 'erro', 'mensagem': 'Item não localizado no servidor!'}), 404
                
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
        
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. Validação rápida da senha
            cur.execute("SELECT senha FROM usuarios WHERE usuario = %s", (session.get('usuario_logado'),))
            dados_u = cur.fetchone()
            user_senha = str(dados_u['senha']) if dados_u else ""
            
            if user_senha == criptografar_sha256(senha):
                lista_ids = [int(x.strip()) for x in str(ids_enviados).split(',') if x.strip().isdigit()]
                
                # 2. Exclusão direta usando NOW() do MySQL (mais rápido que formatar data no Python)
                format_strings = ','.join(['%s'] * len(lista_ids))
                cur.execute(f"""
                    UPDATE arquivos_painel 
                    SET deletado = 1, deletado_em = NOW() 
                    WHERE id IN ({format_strings}) AND deletado = 0
                """, tuple(lista_ids))
                
                conn.commit()
                # 3. Retorno imediato!
                resp = jsonify({'status': 'sucesso'})
                
                # 4. Log acontece APÓS a resposta ao usuário ou de forma mais leve
                # Se ainda estiver lento, tente comentar a linha abaixo
                # registrar_log(f"Enviou para a lixeira IDs: {ids_enviados}")
                
                conn.close()
                return resp
        
        conn.close()
        return jsonify({'status': 'erro', 'mensagem': 'Senha incorreta!'})
    except Exception as e:
        print(f"ERRO NA EXCLUSÃO: {e}")
        return jsonify({'status': 'erro', 'mensagem': 'Erro interno'}), 500
        
@app.route('/salvar-site', methods=['POST'])
def salvar_site():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    nome, url, bloco = request.form.get('nome'), request.form.get('url'), request.form.get('bloco')
    
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url

    if not bloco or str(bloco).strip().lower() in ["", "null", "undefined", "sites jp2 business"]:
        bloco_final = 'sites_jp2'
    else:
        bloco_final = str(bloco).strip()

    # --- ROBÔ DE CAPTURA AUTOMÁTICA DE LOGO (FAVICON) ---
    nome_limpo = "".join(x for x in nome if x.isalnum())
    nome_arquivo_imagem = f"{nome_limpo}.jpeg"
    caminho_salvar_imagem = os.path.join(app.root_path, 'static', 'image', nome_arquivo_imagem)
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=5).read()
        soup = BeautifulSoup(html, 'html.parser')
        icon_link = soup.find('link', rel=re.compile(r'^(shortcut )?icon$', re.I))
        if icon_link and icon_link.get('href'):
            url_icon = icon_link.get('href')
            if not url_icon.startswith('http'):
                url_icon = urljoin(url, url_icon)
            urllib.request.urlretrieve(url_icon, caminho_salvar_imagem)
    except Exception as e:
        print(f"Robô não conseguiu extrair a logo do site: {e}")

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO arquivos_painel (nome_original, bloco, tipo, categoria, caminho_sistema, criado_por, deletado)
                VALUES (%s, %s, 'link', 'sites_jp2', %s, %s, 0)
            """, (nome, bloco_final, url, session.get('nome_exibicao', 'Sistema')))
        conn.commit()
        conn.close()
        registrar_log(f"Incluiu o site institucional: {nome} ({url})")
        return jsonify({'status': 'sucesso'})
    except:
        return jsonify({'status': 'erro'})
        
@app.route('/api/listar-eventos')
def api_listar_eventos():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, titulo, data_evento, data_fim FROM agenda_eventos")
            eventos = cur.fetchall()
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
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO agenda_eventos (titulo, data_evento, data_fim)
                VALUES (%s, %s, %s)
            """, (titulo, data_ini, data_fim))
        conn.commit()
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
        with conn.cursor() as cur:
            cur.execute("SELECT senha FROM usuarios WHERE usuario = %s", (session.get('usuario_logado'),))
            dados_u = cur.fetchone()
            user_senha = str(dados_u['senha']) if dados_u else ""
            
            if user_senha == criptografar_sha256(senha):
                if evento_id and evento_id != "" and evento_id != "undefined" and evento_id != "null":
                    cur.execute("DELETE FROM agenda_eventos WHERE id = %s", (int(evento_id),))
                    registrar_log(f"Apagou o compromisso da agenda ID: {evento_id}")
                elif titulo:
                    cur.execute("DELETE FROM agenda_eventos WHERE titulo LIKE %s", (titulo,))
                    registrar_log(f"Apagou o compromisso da agenda por título: {titulo}")
        conn.commit()
        conn.close()
        return jsonify({'status': 'sucesso'})
    except: return jsonify({'status': 'erro'})

@app.route('/api/resumo-dashboard')
def resumo_dashboard():
    try:
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
        return jsonify({'total_arquivos': total_arquivos, 'total_socios': total_socios, 'proximo_evento': proximo_evento})
    except: return jsonify({'error': 'erro'}), 500

@app.route('/manifest.json')
def manifest(): return send_from_directory('static', 'manifest.json')    

if __name__ == '__main__':
    app.run(debug=True)
