from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from app import get_db_connection
import pandas as pd
import os

bp_financeiro = Blueprint('financeiro', __name__)

@bp_financeiro.route('/api/financeiro/dados')
def api_dados():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM financeiro_emprestimos")
    dados = cursor.fetchall()
    conn.close()
    return jsonify({"dados": dados})

@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    
    # IMPORTAÇÃO AUTOMÁTICA
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM financeiro_emprestimos")
    if cursor.fetchone()['total'] == 0:
        # Lê o CSV e joga no banco
        try:
            df = pd.read_csv("Empréstimo Holding Negócios.xlsx - EMPRÉSTIMO INSTITUTO.csv", header=1)
            for _, row in df.iterrows():
                cursor.execute("INSERT INTO financeiro_emprestimos (entidade, valor_original, saldo_devedor) VALUES (%s, %s, %s)", 
                               ("Instituto", row.get('Valor Inicial', 0), row.get('Valor Final', 0)))
            conn.commit()
        except: pass
    conn.close()
    
    return render_template('financeiro.html')
