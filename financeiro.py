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
        # Conversão de segurança para números puros
        valor = float(dados.get('valor', 0))
        juros = float(dados.get('juros', 0))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. INSERT na tabela 'investimentos' ajustado para as suas colunas reais
        # Colunas reais: nome_investidor, tipo_operacao, valor_inicial, data_inicio, juros_mensais, descricao
        # Certifique-se de que o número de %s (na query) é igual ao número de campos (no segundo parêntese)
        query = """
        INSERT INTO investimentos (nome_investidor, valor_inicial, detalhes, juros_mensais, data_inicio, descricao) 
        VALUES (%s, %s, %s, %s, %s, %s)
       """
       # Pegue a descrição vindo do formulário
       descricao = request.form.get('descricao')

       # Execute passando os valores
       cur.execute(query, (quem, valor, detalhes, juros, mes_ano, descricao))
        
        # 2. Cálculo de juros
        vlr_juros = (valor * (juros / 100)) / 30 * 15
        valor_final = valor + vlr_juros
        
        # 3. INSERT na tabela 'calculo_mensal' ajustado para as colunas reais
        # Colunas reais: investimento_id, mes_referencia, valor_inicial, juros_aplicados, valor_juros, valor_final, pagamento_realizado, saldo_devedor, data_registro
        cur.execute("""
            INSERT INTO calculo_mensal (investimento_id, mes_referencia, valor_inicial, juros_aplicados, valor_juros, valor_final, pagamento_realizado, saldo_devedor, data_registro)
            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, NOW())
        """, (investimento_id, dados['mes_ano'], valor, juros, vlr_juros, valor_final, valor_final))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        return jsonify({'status': 'erro', 'msg': str(e)})
        
@bp_financeiro.route('/api/resumo-investimentos', methods=['GET'])
def resumo_investimentos():
    if 'usuario_logado' not in session:
        return jsonify({'status': 'erro', 'msg': 'Não autorizado'}), 401
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Corrigido o JOIN para usar 'i.id' (conforme sua estrutura)
        query = """
            SELECT 
                i.id,
                i.nome_investidor as credor, 
                i.valor_inicial as valor_investido, 
                i.descricao as empresa, 
                i.juros_mensais as juros, 
                i.data_inicio as mes_ano,
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
