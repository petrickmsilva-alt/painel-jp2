from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from database import get_db_connection
import pandas as pd
import os

bp_financeiro = Blueprint('financeiro', __name__)

@bp_financeiro.route('/api/financeiro/dados')
def api_dados():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Buscamos os dados da tabela que estamos populando
    cursor.execute("SELECT entidade, valor_original, 0 as saldo_devedor FROM financeiro_emprestimos")
    dados = cursor.fetchall()
    conn.close()
    return jsonify(dados)

@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session: 
        return redirect(url_for('tela_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM financeiro_emprestimos")
    resultado = cursor.fetchone()
    
    # Se estiver vazio, tenta importar a planilha (Apenas na primeira vez)
    if resultado['total'] == 0:
        try:
            arquivo = 'Empréstimo Holding Negócios.xlsx'
            if os.path.exists(arquivo):
                # IMPORTANTE: Se o seu arquivo tiver várias abas, 
                # use sheet_name='NOME_DA_ABA' ou sheet_name=0 para a primeira
                df = pd.read_excel(arquivo, sheet_name=0, header=2) 
                
                for _, row in df.iterrows():
                    entidade = str(row.iloc[0]) # Coluna 0: QUEM
                    valor_raw = str(row.iloc[1]) # Coluna 1: VALOR
                    
                    # Limpeza simples do valor
                    valor = valor_raw.replace('R$', '').replace(',', '').strip()
                    
                    if entidade and entidade != 'nan' and valor.replace('.','',1).isdigit():
                        cursor.execute("INSERT INTO financeiro_emprestimos (entidade, valor_original) VALUES (%s, %s)", 
                                       (entidade, float(valor)))
                conn.commit()
        except Exception as e:
            print(f"Erro na importação: {e}")
            
    conn.close()
    return render_template('financeiro.html')
