import os
import hashlib
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, make_response, send_from_directory
from supabase import create_client

# CONFIGURAÇÃO SEGURA: Busca as chaves direto das Variáveis de Ambiente da Render
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://zkdzgpblxorcxxdrmojo.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_KEY:
    raise ValueError("ERRO CRÍTICO: A chave SUPABASE_KEY não foi configurada nas Variáveis de Ambiente da Render!")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_secreta_super_segura_jp2")

def registrar_log(acao):
    try:
        usuario = session.get('nome_exibicao', 'Sistema / Desconhecido')
        ip_usuario = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        supabase.table("logs_auditoria").insert({
            "usuario": usuario, 
            "acao": acao,
            "ip_origem": ip_usuario
        }).execute()
    except Exception as e:
        print(f"ERRO AO REGISTRAR LOG: {e}")

def criptografar_sha256(senha_pura):
    return hashlib.sha256(senha_pura.encode('utf-8')).hexdigest()

@app.route('/login', methods=['GET', 'POST'])
def tela_login():
    if request.method == 'POST':
        u = request.form.get('usuario', '').lower().strip()
        s = request.form.get('senha', '').strip()
        
        try:
            res = supabase.table("usuarios").select("*").eq("usuario", u).execute()
            dados = res.data if hasattr(res, 'data') else (res if isinstance(res, list) else [])
            user = dados[0] if dados else None
            
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
            supabase.table("usuarios").insert({
                "usuario": novo_user, 
                "senha": senha_cripto, 
                "nome_exibicao": nome_exib
            }).execute()
            registrar_log(f"Cadastrou um novo usuário no painel: {novo_user}")
        except Exception as e:
            print(f"Erro cadastro: {e}")
            
    res = supabase.table("usuarios").select("id, usuario, nome_exibicao").execute()
    lista_usuarios = res.data if hasattr(res, 'data') else []
    return render_template('admin_usuarios.html', usuarios=lista_usuarios)

@app.route('/admin/excluir_usuario/<int:usuario_id>', methods=['POST'])
def excluir_usuario(usuario_id):
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    try:
        supabase.table("usuarios").delete().eq("id", usuario_id).execute()
        registrar_log(f"Removeu o usuário ID: {usuario_id} do sistema")
        flash("Sócio removido com sucesso!")
    except Exception as e:
        print(f"Erro ao deletar usuário: {e}")
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/logs')
def admin_logs():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    try:
        res = supabase.table("logs_auditoria").select("*").order("data_registro", desc=True).limit(100).execute()
        lista_logs = res.data if hasattr(res, 'data') else []
    except:
        lista_logs = []
    return render_template('admin_logs.html', logs=lista_logs)

@app.route('/listar')
def listar_arquivos():
    if 'usuario_logado' not in session: return jsonify({'erro': 'Não autorizado'}), 401
    bloco = request.args.get('bloco')
    pasta_pai_id = request.args.get('pasta_pai_id')
    
    try:
        # Query base: filtra apenas pelo bloco e deletado
        query = supabase.table("arquivos_painel").select("*").eq("bloco", bloco).eq("deletado", False)
        
        # Filtro flexível: se tem pasta_pai_id, busca nele. Se não, busca o que é null.
        if pasta_pai_id and str(pasta_pai_id).strip() not in ["null", "undefined", ""]:
            query = query.eq("pasta_pai_id", int(pasta_pai_id))
        else:
            query = query.is_("pasta_pai_id", "null")
            
        res = query.execute()
        linhas = res.data if hasattr(res, 'data') else []
        
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
        res = supabase.table("arquivos_painel").select("id").eq("bloco", bloco).eq("nome_original", ultima_pasta_nome).eq("tipo", "pasta").eq("deletado", False).execute()
        dados = res.data if hasattr(res, 'data') else []
        return jsonify({'pasta_pai_id': dados[0]['id'] if dados else None})
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
        supabase.table("arquivos_painel").insert({
            "nome_original": nome, "bloco": bloco, "categoria": cat, "tipo": "pasta", "pasta_pai_id": p_id, "criado_por": session.get('nome_exibicao', 'Sistema')
        }).execute()
        registrar_log(f"Criou a pasta: {nome} no bloco {bloco}")
        return jsonify({'status': 'sucesso'})
    except:
        return jsonify({'status': 'erro'})

import uuid
import re

@app.route('/upload-avancado', methods=['POST'])
def upload_avancado():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    arquivos = request.files.getlist('arquivos')
    bloco, cat, pai = request.form.get('bloco'), request.form.get('categoria'), request.form.get('pasta_pai_id')
    p_id = int(pai) if (pai and str(pai).strip() not in ["null", "undefined", ""]) else None
    
    try:
        for arq in arquivos:
            if arq.filename == '': continue
            
            # Sanitização de nome para evitar erros no Storage
            nome_limpo = re.sub(r'[^a-zA-Z0-9._-]', '', arq.filename.replace(' ', '_'))
            nome_unico = f"{uuid.uuid4().hex}_{nome_limpo}"
            
            # STREAMING: O arq.stream envia o arquivo em pedaços, evitando estouro de RAM
            supabase.storage.from_("meus-arquivos").upload(
                path=nome_unico, 
                file=arq.stream, 
                file_options={"content-type": arq.content_type}
            )
            
            link = supabase.storage.from_("meus-arquivos").get_public_url(nome_unico)
            
            dados_insercao = {
                "nome_original": arq.filename, 
                "caminho_sistema": link, 
                "bloco": bloco, 
                "categoria": cat, 
                "tipo": "arquivo", 
                "criado_por": session.get('nome_exibicao', 'Sistema')
            }
            if p_id is not None: dados_insercao["pasta_pai_id"] = p_id
            
            supabase.table("arquivos_painel").insert(dados_insercao).execute()
            registrar_log(f"Upload via Streaming: {arq.filename}")
            
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        print(f"ERRO CRÍTICO NO UPLOAD: {e}")
        return jsonify({'status': 'erro', 'mensagem': str(e)})
        
@app.route('/baixar/<int:arquivo_id>')
def baixar_arquivo(arquivo_id):
    if 'usuario_logado' not in session: return "Não autorizado", 401
    try:
        res = supabase.table("arquivos_painel").select("caminho_sistema, nome_original, deletado").eq("id", arquivo_id).execute()
        dados = res.data if hasattr(res, 'data') else []
        if dados and dados[0]['deletado'] != True:
            registrar_log(f"Fez download do arquivo: {dados[0]['nome_original']}")
            if dados[0]['caminho_sistema'].startswith('http'): 
                return redirect(dados[0]['caminho_sistema'])
    except: pass
    return "Arquivo não encontrado", 404

@app.route('/excluir', methods=['POST'])
def excluir_arquivo():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    arq_id, senha = request.form.get('id'), request.form.get('senha', '').strip()
    try:
        res_u = supabase.table("usuarios").select("senha").eq("usuario", session.get('usuario_logado')).execute()
        dados_u = res_u.data if hasattr(res_u, 'data') else (res_u if isinstance(res_u, list) else [])
        user_senha = str(dados_u[0]['senha']) if dados_u else ""
        
        if user_senha == criptografar_sha256(senha):
            res_arq = supabase.table("arquivos_painel").select("nome_original").eq("id", arq_id).execute()
            nome_arq = res_arq.data[0]['nome_original'] if res_arq.data else "Desconhecido"
            
            supabase.table("arquivos_painel").update({
                "deletado": True, 
                "deletado_em": datetime.now().isoformat()
            }).eq("id", arq_id).execute()
            
            registrar_log(f"Enviou para a lixeira o item/pasta: {nome_arq} (ID: {arq_id})")
            return jsonify({'status': 'sucesso'})
        return jsonify({'status': 'erro', 'mensagem': 'Senha incorreta!'})
    except:
        return jsonify({'status': 'erro'})

@app.route('/salvar-site', methods=['POST'])
def salvar_site():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro'}), 401
    nome, url, bloco = request.form.get('nome'), request.form.get('url'), request.form.get('bloco')
    try:
        supabase.table("arquivos_painel").insert({
            "nome_original": nome, "bloco": bloco, "tipo": "link", "categoria": "raiz", "caminho_sistema": url, "criado_por": session.get('nome_exibicao', 'Sistema')
        }).execute()
        registrar_log(f"Incluiu o site institucional: {nome} ({url})")
        return jsonify({'status': 'sucesso'})
    except:
        return jsonify({'status': 'erro'})

@app.route('/api/listar-eventos')
def api_listar_eventos():
    try:
        res = supabase.table("agenda_eventos").select("id, titulo, data_evento, data_fim").execute()
        eventos = res.data if hasattr(res, 'data') else []
        lista_diaria = []
        for ev in eventos:
            titulo, inicio_str, fim_str = ev['titulo'], ev['data_evento'], ev['data_fim'] or ev['data_evento']
            cor = '#dc2626' if "reuniao" in titulo.lower() else ('#7c3aed' if "evento" in titulo.lower() else '#3b82f6')
            try:
                inicio = datetime.strptime(inicio_str, '%Y-%m-%d')
                fim = datetime.strptime(fim_str, '%Y-%m-%d')
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
        supabase.table("agenda_eventos").insert({"titulo": titulo, "data_evento": data_ini, "data_fim": data_fim}).execute()
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
        res_u = supabase.table("usuarios").select("senha").eq("usuario", session.get('usuario_logado')).execute()
        dados_u = res_u.data if hasattr(res_u, 'data') else (res_u if isinstance(res_u, list) else [])
        user_senha = str(dados_u[0]['senha']) if dados_u else ""
        
        if user_senha == criptografar_sha256(senha):
            if evento_id and evento_id != "" and evento_id != "undefined" and evento_id != "null":
                supabase.table("agenda_eventos").delete().eq("id", int(evento_id)).execute()
                registrar_log(f"Apagou o compromisso da agenda ID: {evento_id}")
            elif titulo:
                supabase.table("agenda_eventos").delete().ilike("titulo", titulo).execute()
                registrar_log(f"Apagou o compromisso da agenda por título: {titulo}")
            return jsonify({'status': 'sucesso'})
        return jsonify({'status': 'erro', 'mensagem': 'Senha incorreta!'})
    except: return jsonify({'status': 'erro'})

@app.route('/api/resumo-dashboard')
def resumo_dashboard():
    try:
        res_arq = supabase.table("arquivos_painel").select("id", count="exact").eq("deletado", False).execute()
        total_arquivos = res_arq.count if res_arq.count is not None else 0
        res_soc = supabase.table("usuarios").select("id", count="exact").execute()
        total_socios = res_soc.count if res_soc.count is not None else 0
        hoje = datetime.now().strftime('%Y-%m-%d')
        res_ev = supabase.table("agenda_eventos").select("titulo").gte("data_evento", hoje).order("data_evento", desc=False).limit(1).execute()
        dados_ev = res_ev.data if hasattr(res_ev, 'data') else []
        proximo_evento = dados_ev[0]['titulo'] if dados_ev else "Nenhum"
        return jsonify({'total_arquivos': total_arquivos, 'total_socios': total_socios, 'proximo_evento': proximo_evento})
    except: return jsonify({'error': 'erro'}), 500

@app.route('/manifest.json')
def manifest(): return send_from_directory('static', 'manifest.json')    

if __name__ == '__main__':
    app.run(debug=True)
