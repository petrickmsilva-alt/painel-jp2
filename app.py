import os
import sqlite3
import shutil
from supabase import create_client

# Coloque as suas informações aqui:
SUPABASE_URL = "https://zkdzgpblxorcxxdrmojo.supabase.co" 
SUPABASE_KEY = "sb_secret_9004F4w6cyOWErL5RQJTPQ_rfUdEyEb" 

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, send_from_directory, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
DB_NAME = "banco_painel.db"
import os
print("CAMINHO DO BANCO QUE O FLASK ESTÁ LENDO:", os.path.abspath(DB_NAME))
UPLOAD_FOLDER = "arquivos_sistema"

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = "chave_secreta_super_segura_jp2"

def inicializar_banco():
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        usuario TEXT NOT NULL UNIQUE, 
                        senha TEXT NOT NULL, 
                        nome_exibicao TEXT NOT NULL DEFAULT '')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS arquivos_painel (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nome_original TEXT NOT NULL, 
                        caminho_sistema TEXT, 
                        bloco TEXT NOT NULL, 
                        categoria TEXT NOT NULL, 
                        tipo TEXT NOT NULL DEFAULT 'arquivo', 
                        pasta_pai_id INTEGER DEFAULT NULL, 
                        criado_por TEXT, 
                        data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS agenda_eventos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        titulo TEXT NOT NULL, 
                        data_evento TEXT NOT NULL, 
                        data_fim TEXT, 
                        horario TEXT, 
                        tipo_evento TEXT NOT NULL DEFAULT 'reuniao')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs_auditoria (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        usuario TEXT NOT NULL, 
                        acao TEXT NOT NULL, 
                        data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL,
        senha TEXT NOT NULL
    )
""")
    conexao.commit()
    conexao.close()

def registrar_log(acao):
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    usuario = session.get('nome_exibicao', 'Sistema')
    cursor.execute("INSERT INTO logs_auditoria (usuario, acao) VALUES (?, ?)", (usuario, acao))
    conexao.commit()
    conexao.close()

def realizar_backup():
    try:
        if not os.path.exists('backups'):
            os.makedirs('backups')
        data_atual = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_backup = os.path.join('backups', f"backup_{data_atual}.db")
        shutil.copy2(DB_NAME, nome_backup)
        print(f"BACKUP OK: {nome_backup}")
    except Exception as e:
        print(f"ERRO NO BACKUP: {e}")
        
@app.route('/login', methods=['GET', 'POST'])
def tela_login():
    if request.method == 'POST':
        u = request.form.get('usuario', '').lower().strip()
        s = request.form.get('senha')
        conexao = sqlite3.connect(DB_NAME)
        conexao.row_factory = sqlite3.Row
        cursor = conexao.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario = ?", (u,))
        user = cursor.fetchone()
        conexao.close()
        if user and check_password_hash(user['senha'], s):
            session['usuario_logado'] = user['usuario']
            session['nome_exibicao'] = user['nome_exibicao']
            realizar_backup()
            return redirect(url_for('home'))
        else:
            flash("Login ou senha inválidos!")
            return redirect(url_for('tela_login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    realizar_backup()
    session.clear()
    return redirect(url_for('tela_login'))

import os

@app.route('/')
def home():
    if 'usuario_logado' not in session: 
        return redirect(url_for('tela_login'))
    
    # Debug: Printa o caminho real onde o Flask busca o 'home.html'
    template_path = os.path.join(app.root_path, 'templates', 'home.html')
    print("DEBUG: O Flask está buscando o arquivo em ->", template_path)
    
    return render_template('home.html', nome_sócio=session.get('nome_exibicao', 'Sócio'))

@app.route('/agenda')
def pagina_agenda():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    return render_template('agenda.html', nome_sócio=session.get('nome_exibicao', 'Sócio'))

@app.route('/admin/usuarios', methods=['GET', 'POST'])
def admin_usuarios():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    conexao = sqlite3.connect(DB_NAME)
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()
    if request.method == 'POST':
        novo_user = request.form.get('novo_usuario', '').lower().strip()
        senha_pura = request.form.get('nova_senha')
        nome_exib = request.form.get('nome_exibicao', '')
        try:
            nova_senha = generate_password_hash(senha_pura)
            cursor.execute("INSERT INTO usuarios (usuario, senha, nome_exibicao) VALUES (?, ?, ?)", (novo_user, nova_senha, nome_exib))
            conexao.commit()
            registrar_log(f"Cadastrou novo sócio: {novo_user}")
        except Exception as e:
            print(f"DEBUG ERRO: {e}")
    cursor.execute("SELECT id, usuario, nome_exibicao FROM usuarios")
    lista_usuarios = cursor.fetchall()
    conexao.close()
    return render_template('admin_usuarios.html', usuarios=lista_usuarios)

@app.route('/admin/logs')
def admin_logs():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    conexao = sqlite3.connect(DB_NAME)
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM logs_auditoria ORDER BY data_registro DESC")
    lista_logs = cursor.fetchall()
    conexao.close()
    return render_template('admin_logs.html', logs=lista_logs)

@app.route('/admin/excluir_usuario/<int:usuario_id>', methods=['POST'])
def excluir_usuario(usuario_id):
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    conexao.commit()
    conexao.close()
    flash("Sócio removido com sucesso!")
    return redirect(url_for('admin_usuarios'))

@app.route('/listar')
def listar_arquivos():
    if 'usuario_logado' not in session: return jsonify({'erro': 'Não autorizado'}), 401
    conexao = sqlite3.connect(DB_NAME)
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM arquivos_painel")
    linhas = cursor.fetchall()
    conexao.close()
    return jsonify({'itens': [{'id': l['id'], 'nome': l['nome_original'], 'tipo': l['tipo'], 'caminho': l['caminho_sistema'], 'autor': l['criado_por'] or 'Sistema', 'bloco': l['bloco']} for l in linhas]})

@app.route('/criar-pasta', methods=['POST'])
def criar_pasta():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    nome, bloco = request.form.get('nome'), request.form.get('bloco')
    cat = request.form.get('categoria') or 'raiz'
    pai = request.form.get('pasta_pai_id')
    print(f"DEBUG: Recebi pasta_pai_id como: '{pai}'")
    p_id = int(pai) if (pai and pai != "null" and pai != "undefined") else None
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    cursor.execute("INSERT INTO arquivos_painel (nome_original, bloco, categoria, tipo, pasta_pai_id, criado_por) VALUES (?, ?, ?, 'pasta', ?, ?)", 
                   (nome, bloco, cat, p_id, session.get('nome_exibicao')))
    conexao.commit()
    registrar_log(f"Criou uma nova pasta: {nome}")
    conexao.close()
    return jsonify({'status': 'sucesso'})

@app.route('/upload-avancado', methods=['POST'])
def upload_avancado():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    arquivos = request.files.getlist('arquivos')
    bloco, cat, pai = request.form.get('bloco'), request.form.get('categoria'), request.form.get('pasta_pai_id')
    p_id = int(pai) if (pai and pai != "null") else None
    
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    
    for arq in arquivos:
        if arq.filename == '': continue
        
        # Envia para o Supabase (Bucket 'meus-arquivos')
        # O arquivo é lido como bytes e enviado
        supabase.storage.from_("meus-arquivos").upload(
            path=arq.filename, 
            file=arq.read(),
            file_options={"content-type": arq.content_type}
        )
        # Pega a URL pública
        link = supabase.storage.from_("meus-arquivos").get_public_url(arq.filename)
        
        # Salva o LINK no banco
        cursor.execute("INSERT INTO arquivos_painel (nome_original, caminho_sistema, bloco, categoria, tipo, pasta_pai_id, criado_por) VALUES (?, ?, ?, ?, 'arquivo', ?, ?)", 
                       (arq.filename, link, bloco, cat, p_id, session.get('nome_exibicao')))
    
    conexao.commit()
    conexao.close()
    return jsonify({'status': 'sucesso'})

@app.route('/baixar/<int:arquivo_id>')
def baixar_arquivo(arquivo_id):
    if 'usuario_logado' not in session: return "Não autorizado", 401
    conexao = sqlite3.connect(DB_NAME)
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()
    cursor.execute("SELECT caminho_sistema FROM arquivos_painel WHERE id = ?", (arquivo_id,))
    res = cursor.fetchone()
    conexao.close()
    
    if res and res['caminho_sistema'].startswith('http'):
        # Redireciona o navegador direto para o arquivo no Supabase
        return redirect(res['caminho_sistema'])
    return "Arquivo não encontrado", 404

@app.route('/excluir', methods=['POST'])
def excluir_arquivo():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    arq_id, senha = request.form.get('id'), request.form.get('senha')
    
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    
    # 1. Verifica a senha
    cursor.execute("SELECT senha FROM usuarios WHERE usuario = ?", (session.get('usuario_logado'),))
    u = cursor.fetchone()
    if not u or not check_password_hash(u[0], senha):
        conexao.close()
        return jsonify({'status': 'erro', 'mensagem': 'Senha incorreta!'})

    # 2. Executa a deleção na tabela CORRETA (arquivos_painel)
    cursor.execute("DELETE FROM arquivos_painel WHERE id = ?", (arq_id,))
    
    # 3. O 'commit' é vital aqui para salvar no arquivo .db
    conexao.commit() 
    conexao.close()
    
    return jsonify({'status': 'sucesso'})

@app.route('/salvar-site', methods=['POST'])
def salvar_site():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    nome, url, bloco = request.form.get('nome'), request.form.get('url'), request.form.get('bloco')
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    cursor.execute("INSERT INTO arquivos_painel (nome_original, bloco, tipo, categoria, criado_por, caminho_sistema) VALUES (?, ?, 'link', 'raiz', ?, ?)", 
                   (nome, bloco, session.get('nome_exibicao'), url))
    conexao.commit()
    conexao.close()
    return jsonify({'status': 'sucesso'})

@app.route('/api/listar-eventos')
def api_listar_eventos():
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    cursor.execute("SELECT titulo, data_evento, data_fim FROM agenda_eventos")
    eventos = cursor.fetchall()
    conexao.close()
    
    lista_diaria = []
    for ev in eventos:
        titulo, inicio_str, fim_str = ev
        cor = '#dc2626' if "reuniao" in titulo.lower() else ('#7c3aed' if "evento" in titulo.lower() else '#3b82f6')
        try:
            inicio = datetime.strptime(inicio_str, '%Y-%m-%d')
            fim = datetime.strptime(fim_str, '%Y-%m-%d')
            for i in range((fim - inicio).days + 1):
                lista_diaria.append({'title': titulo, 'start': (inicio + timedelta(days=i)).strftime('%Y-%m-%d'), 'allDay': True, 'color': cor})
        except:
            continue

    # O "COMANDO MATADOR" DE CACHE:
    resp = make_response(jsonify(lista_diaria))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/adicionar-evento', methods=['POST'])
def calendar_adicionar():
    titulo = request.form.get('titulo')
    # Pegamos exatamente o que vem do formulário
    data_ini = request.form.get('dataReuniaoInput') 
    data_fim = request.form.get('data_fim') or data_ini

    # Se a data estiver vazia, retorna um erro em vez de salvar errado
    if not data_ini:
        return {"status": "erro", "mensagem": "Data não enviada!"}, 400

    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    cursor.execute("INSERT INTO agenda_eventos (titulo, data_evento, data_fim) VALUES (?, ?, ?)", (titulo, data_ini, data_fim))
    conexao.commit()
    conexao.close()
    return {"status": "sucesso"}, 200

@app.route('/api/resumo-dashboard')
def resumo_dashboard():
    try:
        # Usando a variável DB_NAME para garantir consistência
        conexao = sqlite3.connect(DB_NAME) 
        cursor = conexao.cursor()

        # Contar Arquivos e Sócios
        cursor.execute("SELECT COUNT(*) FROM arquivos_painel")
        total_arquivos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_socios = cursor.fetchone()[0]

        # Ajuste para a coluna real 'data_evento'
        hoje = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("SELECT titulo FROM agenda_eventos WHERE data_evento >= ? ORDER BY data_evento ASC LIMIT 1", (hoje,))
        evento = cursor.fetchone()
        proximo_evento = evento[0] if evento else "Nenhum"

        conexao.close()
        
        return jsonify({
            'total_arquivos': total_arquivos,
            'total_socios': total_socios,
            'proximo_evento': proximo_evento
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/limpar-agenda-teste')
def limpar_agenda():
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM agenda_eventos")
    conexao.commit()
    conexao.close()
    return "Agenda limpa com sucesso! Agora você pode voltar e tentar inserir um novo evento."
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')    
    
if __name__ == '__main__':
    inicializar_banco()
    app.run(debug=True)
