from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import get_db_connection
from datetime import datetime

bp_financeiro = Blueprint('financeiro', __name__)

# --- ROTAS DE PÁGINA ---
@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    return render_template('financeiro.html')

# --- ROTAS DE EMPRESAS (DINÂMICO) ---
@bp_financeiro.route('/api/empresas', methods=['GET'])
def listar_empresas():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM empresas")
    empresas = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({'status': 'sucesso', 'dados': empresas})

@bp_financeiro.route('/api/adicionar-empresa', methods=['POST'])
def adicionar_empresa():
    dados = request.form
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO empresas (nome, cnpj, ramo_atividade) VALUES (%s, %s, %s)", 
                (dados['nome'], dados['cnpj'], dados['ramo_atividade']))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'status': 'sucesso'})

# --- ROTA DE CADASTRO DE INVESTIMENTO (ATUALIZADA) ---
@bp_financeiro.route('/api/adicionar-investimento', methods=['POST'])
def adicionar_investimento():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Query de inserção usando os nomes de colunas que verificamos na sua imagem
        query = """
            INSERT INTO investimentos 
            (nome_investidor, valor_inicial, juros_mensais, data_inicio, descricao, captador, tipo_recurso, finalidade, data_pgto) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            request.form.get('quem'), 
            request.form.get('valor'), 
            request.form.get('juros'), 
            request.form.get('data_recurso'), 
            request.form.get('descricao'),
            request.form.get('captador'),
            request.form.get('tipo_recurso'),
            request.form.get('finalidade'),
            request.form.get('data_pgto')
        )
        
        cur.execute(query, params)
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'sucesso', 'msg': 'Investimento salvo com sucesso!'})
    except Exception as e:
        return jsonify({'status': 'erro', 'msg': str(e)})

# --- ROTA DE RESUMO ---
@bp_financeiro.route('/api/resumo-investimentos', methods=['GET'])
def resumo_investimentos():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Query ajustada para as novas colunas
        query = "SELECT id, nome_investidor as credor, valor_inicial as valor_investido, juros_mensais as juros, data_inicio as mes_ano, descricao, captador, tipo_recurso, finalidade, data_pgto FROM investimentos"
        cur.execute(query)
        columns = [col[0] for col in cur.description]
        dados = [dict(zip(columns, row)) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        return jsonify({'status': 'sucesso', 'dados': dados})
    except Exception as e:
        return jsonify({'status': 'erro', 'msg': str(e)})

@bp_financeiro.route('/api/excluir-investimento/<int:id>', methods=['DELETE'])
def excluir_investimento(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM investimentos WHERE id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'msg': str(e)})
