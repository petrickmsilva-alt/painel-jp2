from flask import Blueprint, render_template, session, redirect
from app import get_db_connection
import pandas as pd

bp_financeiro = Blueprint('financeiro', __name__)

@bp_financeiro.route('/api/financeiro/dados')
def api_dados():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT entidade, valor_original, 0 as saldo_devedor FROM financeiro_emprestimos")
    dados = cursor.fetchall()
    conn.close()
    return {"dados": dados} # Ajustado para o formato que seu HTML espera

@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM financeiro_emprestimos")
    
    if cursor.fetchone()['total'] == 0:
        try:
            # Lendo sem cabeçalho fixo para não dar erro
            df = pd.read_excel('Empréstimo Holding Negócios.xlsx', header=None)
            # Pega a linha 3 (que parece ter os dados, baseando no seu CSV)
            # Vamos pegar a coluna 0 (Quem) e 1 (Valor)
            for i, row in df.iterrows():
                if i > 2: # Pula as linhas de título
                    entidade = str(row[0])
                    valor = str(row[1]).replace('R$', '').replace(',', '.')
                    if entidade and entidade != 'nan':
                        cursor.execute("INSERT INTO financeiro_emprestimos (entidade, valor_original) VALUES (%s, %s)", 
                                       (entidade, valor))
            conn.commit()
        except Exception as e:
            print(f"Erro detalhado: {e}")
            
    conn.close()
    return render_template('financeiro.html')
