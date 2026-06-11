from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import get_db_connection
from datetime import datetime

bp_financeiro = Blueprint('financeiro', __name__)

# Adicione isso temporariamente no seu financeiro.py para testar
@bp_financeiro.route('/api/testar-colunas')
def testar_colunas():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DESCRIBE investimentos") # Ou PRAGMA table_info(investimentos) se for SQLite
    colunas = cur.fetchall()
    conn.close()
    return jsonify({'colunas': [c[0] for c in colunas]})

# Rota para renderizar a página do financeiro
@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))
    return render_template('financeiro.html')

# Rota para renderizar o resumo
@bp_financeiro.route('/financeiro/resumo')
def pagina_resumo():
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))
    return render_template('resumo.html')

# Lógica de cálculo mensal
def calcular_juros_mensal(valor_inicial, percentual_juros):
    # Converte para float garantindo que não haverá erro de tipo
    return (float(valor_inicial) * (float(percentual_juros) / 100)) / 30 * 15

@bp_financeiro.route('/api/adicionar-investimento', methods=['POST'])
def adicionar_investimento():
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    
    dados = request.form
    try:
        valor = float(dados.get('valor', 0))
        juros = float(dados.get('juros', 0))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # INSERT corrigido com os nomes exatos das colunas da sua imagem
        cur.execute("""
            INSERT INTO investimentos (nome_investidor, valor_inicial, descricao, mes_ano, juros_mensais) 
            VALUES (%s, %s, %s, %s, %s)
        """, (dados['quem'], valor, dados['detalhes'], dados['mes_ano'], juros))
        
        investimento_id = cur.lastrowid
        
        # Cálculo
        vlr_juros = (valor * (juros / 100)) / 30 * 15
        valor_final = valor + vlr_juros
        
        # INSERT em calculo_mensal corrigido
        cur.execute("""
            INSERT INTO calculo_mensal (idinvestimento, id_mes_referencia, valor_inicial, juros_aplicados, valor_juros, valor_final, saldo_devedor, data_registro)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (investimento_id, dados['mes_ano'], valor, juros, vlr_juros, valor_final, valor_final))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'msg': str(e)})
        
# Rota de Resumo para a Tela de Racional
@bp_financeiro.route('/api/resumo-investimentos', methods=['GET'])
def resumo_investimentos():
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    
    try:
        conn = get_db_connection()
        # O 'dictionary=True' depende do seu conector. Se der erro, use o padrão sem o argumento.
        cur = conn.cursor(dictionary=True) 
        
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
