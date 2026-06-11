from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import get_db_connection
from datetime import datetime

bp_financeiro = Blueprint('financeiro', __name__)

# Adicione esta nova rota no seu arquivo financeiro.py
@bp_financeiro.route('/financeiro/resumo')
def pagina_resumo():
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))
    return render_template('resumo.html')

# Rota para renderizar a página do financeiro
@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))
    return render_template('financeiro.html')

# Lógica de cálculo mensal
def calcular_juros_mensal(valor_inicial, percentual_juros):
    return (float(valor_inicial) * (float(percentual_juros) / 100)) / 30 * 15

@bp_financeiro.route('/api/adicionar-investimento', methods=['POST'])
def adicionar_investimento():
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    
    dados = request.form
    valor = dados.get('valor')
    juros = dados.get('juros')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Insere na tabela de investimentos
        cur.execute("""
            INSERT INTO investimentos (quem, valor, detalhes, mes_ano, juros) 
            VALUES (%s, %s, %s, %s, %s)
        """, (dados['quem'], valor, dados['detalhes'], dados['mes_ano'], juros))
        
        investimento_id = cur.lastrowid
        
        # 2. Calcula o Juros inicial e insere na tabela de calculo_mensal
        vlr_juros = calcular_juros_mensal(valor, juros)
        valor_mais_juros = float(valor) + vlr_juros
        
        cur.execute("""
            INSERT INTO calculo_mensal (investimento_id, mes, valor_inicial, juros, vlr_juros, valor_mais_juros, saldo_devedor)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (investimento_id, datetime.now().strftime('%B'), valor, juros, vlr_juros, valor_mais_juros, valor_mais_juros))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'msg': str(e)})

# --- NOVO TIJOLO: ROTA DE RESUMO PARA A TELA DE RACIONAL ---
@bp_financeiro.route('/api/resumo-investimentos', methods=['GET'])
def resumo_investimentos():
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True) # Retorna como dicionário para facilitar o JSON
        
        # Query que cruza o cadastro com o cálculo mensal
        query = """
            SELECT 
                i.quem as credor, 
                i.detalhes as empresa, 
                i.valor as valor_investido, 
                c.valor_final, 
                c.saldo_devedor 
            FROM investimentos i
            LEFT JOIN calculo_mensal c ON i.id = c.investimento_id
        """
        cur.execute(query)
        dados = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({'status': 'sucesso', 'dados': dados})
    except Exception as e:
        return jsonify({'status': 'erro', 'msg': str(e)})
