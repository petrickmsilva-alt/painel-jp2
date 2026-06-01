import os
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, make_response, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client

# Configurações do Supabase (Mantendo suas chaves originais)
SUPABASE_URL = "https://zkdzgpblxorcxxdrmojo.supabase.co" 
SUPABASE_KEY = "sb_publishable_ehLQ5mAA1T_hBGh1YK4KpA_DQ7dxvM6" 

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)
app.secret_key = "chave_secreta_super_segura_jp2"

def registrar_log(acao):
    try:
        usuario = session.get('nome_exibicao', 'Sistema')
        supabase.table("logs_auditoria").insert({"usuario": usuario, "acao": acao}).execute()
    except Exception as e:
        print(f"ERRO AO REGISTRAR LOG: {e}")

@app.route('/login', methods=['GET', 'POST'])
def tela_login():
    if request.method == 'POST':
        u = request.form.get('usuario', '').lower().strip()
        s = request.form.get('senha')
        
        try:
            res = supabase.table("usuarios").select("*").eq("usuario", u).execute()
            user = res.data[0] if res.data else None
            
            if user and check_password_hash(user['senha'], s):
                session['usuario_logado'] = user['usuario']
                session['nome_exibicao'] = user['nome_exibicao']
                registrar_log("Realizou login no sistema")
                return redirect(url_for('home'))
            else:
                flash("Login ou senha inválidos!")
                return redirect(url_for('tela_login'))
        except Exception as e:
            print(f"Erro no Login: {e}")
            flash("Erro de conexão com o banco de dados.")
            return redirect(url_for('tela_login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    registrar_log("Realizou logout no sistema")
    session.clear()
    return redirect(url_for('tela_login'))

@app.route('/')
def home():
    if 'usuario_logado' not in session: 
        return redirect(url_for('tela_login'))
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
        senha_pura = request.form.get('nova_senha')
        nome_exib = request.form.get('nome_exibicao', '')
        try:
            nova_senha = generate_password_hash(senha_pura)
            supabase.table("usuarios").insert({
                "usuario": novo_user, 
                "senha": nova_senha, 
                "nome_exibicao": nome_exib
            }).execute()
            registrar_log(f"Cadastrou novo sócio: {novo_user}")
        except Exception as e:
            print(f"DEBUG ERRO CADASTRO SÓCIO: {e}")
            
    res = supabase.table("usuarios").select("id, usuario, nome_exibicao").execute()
    lista_usuarios = res.data if res.data else []
    return render_template('admin_usuarios.html', usuarios=lista_usuarios)

@app.route('/admin/excluir_usuario/<int:usuario_id>', methods=['POST'])
def excluir_usuario(usuario_id):
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    try:
        supabase.table("usuarios").delete().eq("id", usuario_id).execute()
        flash("Sócio removido com sucesso!")
    except Exception as e:
        print(f"Erro ao deletar usuário: {e}")
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/logs')
def admin_logs():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    res = supabase.table("logs_auditoria").select("*").order("data_registro", desc=True).execute()
    lista_logs = res.data if res.data else []
    return render_template('admin_logs.html', logs=lista_logs)

@app.route('/listar')
def listar_arquivos():
    if 'usuario_logado' not in session: return jsonify({'erro': 'Não autorizado'}), 401
    
    bloco = request.args.get('bloco')
    categoria = request.args.get('categoria', 'raiz')
    pasta_pai_id = request.args.get('pasta_pai_id')

    try:
        query = supabase.table("arquivos_painel").select("*").eq("bloco", bloco)
        
        if pasta_pai_id and pasta_pai_id != "null" and pasta_pai_id != "undefined" and pasta_pai_id != "":
            res = query.eq("pasta_pai_id", int(pasta_pai_id)).execute()
        else:
            res = query.is_("pasta_pai_id", "null").execute()
            
        linhas = res.data if res.data else []
        
        itens_formatados = []
        for l in linhas:
            if l['tipo'] == 'link' and bloco != 'sites_jp2': 
                continue
            itens_formatados.append({
                'id': l['id'], 
                'nome': l['nome_original'], 
                'tipo': l['tipo'], 
                'caminho': l['caminho_sistema'], 
                'autor': l['criado_por'] or 'Sistema', 
                'bloco': l['bloco'],
                'categoria': l['categoria'],
                'pasta_pai_id': l['pasta_pai_id']
            })
        return jsonify({'itens': itens_formatados})
    except Exception as e:
        print(f"Erro na listagem: {e}")
        return jsonify({'itens': []})

@app.route('/obter-pai-id')
def obter_pai_id():
    if 'usuario_logado' not in session: return jsonify({'pasta_pai_id': None}), 401
    bloco = request.args.get('bloco')
    caminho = request.args.get('caminho', '')
    
    partes = caminho.split(' ➔ ')
    if len(partes) <= 1:
        return jsonify({'pasta_pai_id': None})
        
    ultima_pasta_nome = partes[-1]
    
    try:
        res = supabase.table("arquivos_painel").select("id").eq("bloco", bloco).eq("nome_original", ultima_pasta_nome).eq("tipo", "pasta").execute()
        return jsonify({'pasta_pai_id': res.data[0]['id'] if res.data else None})
    except:
        return jsonify({'pasta_pai_id': None})

@app.route('/criar-pasta', methods=['POST'])
def criar_pasta():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    nome, bloco = request.form.get('nome'), request.form.get('bloco')
    cat = request.form.get('categoria') or 'raiz'
    pai = request.form.get('pasta_pai_id')
    
    p_id = int(pai) if (pai and pai != "null" and pai != "undefined" and pai != "") else None
    
    try:
        supabase.table("arquivos_painel").insert({
            "nome_original": nome,
            "bloco": bloco,
            "categoria": cat,
            "tipo": "pasta",
            "pasta_pai_id": p_id,
            "criado_por": session.get('nome_exibicao')
        }).execute()
        registrar_log(f"Criou uma nova pasta: {nome}")
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        print(f"Erro ao criar pasta: {e}")
        return jsonify({'status': 'erro'})

@app.route('/upload-avancado', methods=['POST'])
def upload_avancado():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    arquivos = request.files.getlist('arquivos')
    bloco, cat, pai = request.form.get('bloco'), request.form.get('categoria'), request.form.get('pasta_pai_id')
    p_id = int(pai) if (pai and pai != "null" and pai != "undefined" and pai != "") else None
    
    try:
        for arq in arquivos:
            if arq.filename == '': continue
            
            supabase.storage.from_("meus-arquivos").upload(
                path=arq.filename, 
                file=arq.read(),
                file_options={"content-type": arq.content_type}
            )
            link = supabase.storage.from_("meus-arquivos").get_public_url(arq.filename)
            
            supabase.table("arquivos_painel").insert({
                "nome_original": arq.filename,
                "caminho_sistema": link,
                "bloco": bloco,
                "categoria": cat,
                "tipo": "arquivo",
                "pasta_pai_id": p_id,
                "criado_por": session.get('nome_exibicao')
            }).execute()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        print(f"Erro no upload: {e}")
        return jsonify({'status': 'erro'})

@app.route('/baixar/<int:arquivo_id>')
def baixar_arquivo(arquivo_id):
    if 'usuario_logado' not in session: return "Não autorizado", 401
    try:
        res = supabase.table("arquivos_painel").select("caminho_sistema").eq("id", arquivo_id).execute()
        if res.data and res.data[0]['caminho_sistema'].startswith('http'):
            return redirect(res.data[0]['caminho_sistema'])
    except Exception as e:
        print(f"Erro ao baixar: {e}")
    return "Arquivo não encontrado", 404

@app.route('/excluir', methods=['POST'])
def excluir_arquivo():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    arq_id, senha = request.form.get('id'), request.form.get('senha')
    
    try:
        res_u = supabase.table("usuarios").select("senha").eq("usuario", session.get('usuario_logado')).execute()
        user_senha = res_u.data[0]['senha'] if res_u.data else ""
        
        if not user_senha or not check_password_hash(user_senha, senha):
            return jsonify({'status': 'erro', 'mensagem': 'Senha incorreta!'})

        supabase.table("arquivos_painel").delete().eq("id", arq_id).execute()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        print(f"Erro ao excluir: {e}")
        return jsonify({'status': 'erro'})

@app.route('/salvar-site', methods=['POST'])
def salvar_site():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    nome, url, bloco = request.form.get('nome'), request.form.get('url'), request.form.get('bloco')
    try:
        supabase.table("arquivos_painel").insert({
            "nome_original": nome,
            "bloco": bloco,
            "tipo": "link",
            "categoria": "raiz",
            "caminho_sistema": url,
            "criado_por": session.get('nome_exibicao')
        }).execute()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        print(f"Erro ao salvar site: {e}")
        return jsonify({'status': 'erro'})

@app.route('/api/listar-eventos')
def api_listar_eventos():
    try:
        res = supabase.table("agenda_eventos").select("titulo, data_evento, data_fim").execute()
        eventos = res.data if res.data else []
        
        lista_diaria = []
        for ev in eventos:
            titulo = ev['titulo']
            inicio_str = ev['data_evento']
            fim_str = ev['data_fim'] or inicio_str
            cor = '#dc2626' if "reuniao" in titulo.lower() else ('#7c3aed' if "evento" in titulo.lower() else '#3b82f6')
            try:
                inicio = datetime.strptime(inicio_str, '%Y-%m-%d')
                fim = datetime.strptime(fim_str, '%Y-%m-%d')
                for i in range((fim - inicio).days + 1):
                    lista_diaria.append({'title': titulo, 'start': (inicio + timedelta(days=i)).strftime('%Y-%m-%d'), 'allDay': True, 'color': cor})
            except:
                continue

        resp = make_response(jsonify(lista_diaria))
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
    except:
        return jsonify([])

@app.route('/adicionar-evento', methods=['POST'])
def calendar_adicionar():
    titulo = request.form.get('titulo')
    data_ini = request.form.get('dataReuniaoInput') 
    data_fim = request.form.get('data_fim') or data_ini

    if not data_ini:
        return {"status": "erro", "mensagem": "Data não enviada!"}, 400

    try:
        supabase.table("agenda_eventos").insert({
            "titulo": titulo,
            "data_evento": data_ini,
            "data_fim": data_fim
        }).execute()
        return {"status": "sucesso"}, 200
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}, 500

@app.route('/api/resumo-dashboard')
def resumo_dashboard():
    try:
        res_arq = supabase.table("arquivos_painel").select("id", count="exact").execute()
        total_arquivos = res_arq.count if res_arq.count is not None else 0

        res_soc = supabase.table("usuarios").select("id", count="exact").execute()
        total_socios = res_soc.count if res_soc.count is not None else 0

        hoje = datetime.now().strftime('%Y-%m-%d')
        res_ev = supabase.table("agenda_eventos").select("titulo").gte("data_evento", hoje).order("data_evento", desc=False).limit(1).execute()
        proximo_evento = res_ev.data[0]['titulo'] if res_ev.data else "Nenhum"

        return jsonify({
            'total_arquivos': total_arquivos,
            'total_socios': total_socios,
            'proximo_evento': proximo_evento
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')    
    
if __name__ == '__main__':
    app.run(debug=True)
