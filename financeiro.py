from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from utils import get_db_connection
import pandas as pd
import os

bp_financeiro = Blueprint('financeiro', __name__)

def rodar_importacao_automatica():
    # Caminho dos arquivos (certifique-se de que estão na raiz do projeto no GitHub)
    arquivos = ["Empréstimo Holding Negócios.xlsx - EMPRÉSTIMO INSTITUTO.csv"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for nome_arquivo in arquivos:
        if os.path.exists(nome_arquivo):
            df = pd.read_csv(nome_arquivo, header=1)
            for _, row in df.iterrows():
                # Insere no banco
                cursor.execute("INSERT INTO financeiro_emprestimos (entidade, valor_original) VALUES (%s, %s)", 
                               (nome_arquivo, row.get('Valor Inicial', 0)))
    conn.commit()
    conn.close()

@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    
    # Roda a importação ao abrir a página (ou você pode remover isso depois de importar)
    try: rodar_importacao_automatica()
    except: pass 
    
    return render_template('financeiro.html')
