from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import get_db_connection
from datetime import datetime

bp_financeiro = Blueprint('financeiro', __name__)

# Rota para renderizar a página do financeiro
@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session:
        return redirect(url_for('tela_login'))
    return render_template('financeiro.html')

# Lógica de cálculo mensal (O "Motor" do SCRIPT.txt)
def calcular_juros_mensal(valor_inicial, percentual_juros):
    # Regra: (VALOR INICIAL * JUROS) / 30 * 15
    return (float(valor_inicial) * (float(percentual_juros) / 100)) / 30 * 15

@bp_financeiro.route('/api/adicionar-investimento', methods=['POST'])
def adicionar_investimento():
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    
    dados = request.form
    valor = dados.get('valor')
    juros = dados.get('juros')
    
    # Exemplo de como salvar no banco e calcular o primeiro mês
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
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
        conn.close()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'msg': str(e)})
