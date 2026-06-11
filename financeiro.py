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
    conn = get_db_connection()
    cur = conn.cursor()
    # Certifique-se de que a ordem dos campos aqui bate com o que você espera
    cur.execute("SELECT id, nome, cnpj, ramo_atividade FROM empresas")
    
    # Criamos uma lista de dicionários manualmente
    empresas = []
    for row in cur.fetchall():
        empresas.append({
            'id': row[0],
            'nome': row[1],
            'cnpj': row[2],
            'ramo_atividade': row[3]
        })
    
    cur.close()
    conn.close()
    
    # Retorna o JSON estruturado
    return jsonify({'status': 'sucesso', 'dados': empresas})

@bp_financeiro.route('/api/adicionar-empresa', methods=['POST'])
def adicionar_empresa():
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

@bp_financeiro.route('/api/excluir-empresa/<int:id>', methods=['DELETE'])
def excluir_empresa(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM empresas WHERE id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

# --- ROTAS DE INVESTIMENTOS ---
@bp_financeiro.route('/api/resumo-investimentos', methods=['GET'])
def resumo_investimentos():
    if 'usuario_logado' not in session: return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = """SELECT id, nome_investidor as credor, valor_inicial as valor_investido, 
                   juros_mensais as juros, captador, tipo_recurso, finalidade, data_pgto 
                   FROM investimentos"""
        cur.execute(query)
        columns = [col[0] for col in cur.description]
        dados = [dict(zip(columns, row)) for row in cur.fetchall()]
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
