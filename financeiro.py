from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from app import get_db_connection
import pandas as pd

bp_financeiro = Blueprint('financeiro', __name__)

@bp_financeiro.route('/api/financeiro/dados')
def api_dados():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM financeiro_emprestimos")
    dados = cursor.fetchall()
    conn.close()
    return jsonify(dados)

@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    
    # IMPORTAÇÃO DO EXCEL
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM financeiro_emprestimos")
    
    if cursor.fetchone()['total'] == 0:
        try:
            # Lendo o Excel (o pandas usa o openpyxl que pedimos para instalar)
            df = pd.read_excel('Empréstimo Holding Negócios.xlsx', header=1)
            for _, row in df.iterrows():
                entidade = str(row.get('QUEM', 'Desconhecido'))
                valor = float(row.get('VALOR', 0))
                cursor.execute("INSERT INTO financeiro_emprestimos (entidade, valor_original) VALUES (%s, %s)", 
                               (entidade, valor))
            conn.commit()
        except Exception as e:
            print(f"Erro na importação: {e}")
            
    conn.close()
    return render_template('financeiro.html')
