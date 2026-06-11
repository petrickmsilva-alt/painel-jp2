from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import get_db_connection
from datetime import datetime

bp_financeiro = Blueprint('financeiro', __name__)

@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))
    return render_template('financeiro.html')

@bp_financeiro.route('/financeiro/resumo')
def pagina_resumo():
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))
    return render_template('resumo.html')

@bp_financeiro.route('/api/adicionar-investimento', methods=['POST'])
def adicionar_investimento():
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    
    # Captura apenas os campos que sabemos que existem no banco
    quem = request.form.get('quem')
    valor = request.form.get('valor')
    juros = request.form.get('juros')
    mes_ano = request.form.get('mes_ano')
    descricao = request.form.get('descricao')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Query LIMPA: sem a coluna 'detalhes'
        query = """
            INSERT INTO investimentos (nome_investidor, valor_inicial, juros_mensais, data_inicio, descricao) 
            VALUES (%s, %s, %s, %s, %s)
        """
        
        # Execução com 5 parâmetros (exatamente como na query acima)
        cur.execute(query, (quem, valor, juros, mes_ano, descricao))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'sucesso', 'msg': 'Investimento salvo!'})
    except Exception as e:
        return jsonify({'status': 'erro', 'msg': str(e)})
               
@bp_financeiro.route('/api/resumo-investimentos', methods=['GET'])
def resumo_investimentos():
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT 
                i.id,
                i.nome_investidor as credor, 
                i.valor_inicial as valor_investido, 
                i.detalhes as empresa, 
                i.juros_mensais as juros, 
                i.data_inicio as mes_ano,
                i.descricao,
                c.valor_final,
                c.saldo_devedor
            FROM investimentos i
            LEFT JOIN calculo_mensal c ON i.id = c.investimento_id
        """
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
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM calculo_mensal WHERE investimento_id = %s", (id,))
        cur.execute("DELETE FROM investimentos WHERE id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'msg': str(e)})
