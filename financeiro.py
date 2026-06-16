from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import get_db_connection

bp_financeiro = Blueprint('financeiro', __name__)

# --- ROTAS DE PÁGINA ---
@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session: 
        return redirect(url_for('tela_login'))
    return render_template('financeiro.html')

# --- ROTAS DE EMPRESAS ---
@bp_financeiro.route('/api/empresas', methods=['GET'])
def listar_empresas():
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'mensagem': 'Nao autorizado'}), 401
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, nome, cnpj, ramo_atividade FROM empresas")
        # Como o DictCursor já retorna dicionários, basta usar fetchall()
        dados = cur.fetchall() 
        cur.close()
        conn.close()
        return jsonify({'status': 'sucesso', 'dados': dados})
    except Exception as e:
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

@bp_financeiro.route('/api/adicionar-empresa', methods=['POST'])
def adicionar_empresa():
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'mensagem': 'Nao autorizado'}), 401
    nome = request.form.get('nome')
    cnpj = request.form.get('cnpj')
    ramo = request.form.get('ramo_atividade')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO empresas (nome, cnpj, ramo_atividade) VALUES (%s, %s, %s)", (nome, cnpj, ramo))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'status': 'sucesso'})

@bp_financeiro.route('/api/excluir-empresa/<id>', methods=['DELETE'])
def excluir_empresa(id):
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'mensagem': 'Nao autorizado'}), 401
    conn = get_db_connection()
    cur = conn.cursor()
    # O SQL vai funcionar mesmo se o id chegar como string
    cur.execute("DELETE FROM empresas WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'status': 'sucesso'})
    
# --- ROTAS DE INVESTIMENTOS ---
@bp_financeiro.route('/api/resumo-investimentos', methods=['GET'])
def resumo_investimentos():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Removi os "AS" para manter os nomes que o JS já está usando
        query = """SELECT id, nome_investidor, valor_inicial, juros_mensais, 
                          captador, tipo_operacao, finalidade, data_pgto 
                   FROM investimentos"""
        cur.execute(query)
        # Como você usa o DictCursor no database.py, o fetchall() já retorna dicionários!
        # Não precisa do zip nem da lista de colunas.
        dados = cur.fetchall() 
        cur.close()
        conn.close()
        return jsonify({'status': 'sucesso', 'dados': dados})
    except Exception as e:
        return jsonify({'status': 'erro', 'msg': str(e)})

@bp_financeiro.route('/api/adicionar-investimento', methods=['POST'])
def adicionar_investimento():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = """INSERT INTO investimentos 
                (nome_investidor, valor_inicial, juros_mensais, data_inicio, captador, tipo_recurso, finalidade, data_pgto) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        params = (
            request.form.get('quem'), request.form.get('valor'), request.form.get('juros'), 
            request.form.get('data_recurso'), request.form.get('captador'),
            request.form.get('tipo_recurso'), request.form.get('finalidade'),
            request.form.get('data_pgto')
        )
        cur.execute(query, params)
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'msg': str(e)})

@bp_financeiro.route('/api/excluir-investimento/<int:id>', methods=['DELETE'])
def excluir_investimento(id):
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'msg': 'Nao autorizado'}), 401
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
