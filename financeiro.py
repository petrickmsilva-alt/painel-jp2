from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from utils import get_db_connection
import pandas as pd
import os

bp_financeiro = Blueprint('financeiro', __name__)

def rodar_importacao_uma_vez():
    # Verifica se já temos dados na tabela para não importar duplicado
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM financeiro_emprestimos")
    resultado = cursor.fetchone()
    
    # Se a tabela estiver vazia (count é 0), a gente importa
    if resultado['COUNT(*)'] == 0:
        arquivos = [f for f in os.listdir('.') if f.endswith('.csv')]
        for nome_arquivo in arquivos:
            try:
                # header=1 pula as linhas iniciais inúteis
                df = pd.read_csv(nome_arquivo, header=1)
                for _, row in df.iterrows():
                    # Ajuste aqui os nomes das colunas conforme o seu CSV
                    entidade = nome_arquivo.replace('.csv', '')
                    valor = row.get('Valor Inicial', 0)
                    cursor.execute("INSERT INTO financeiro_emprestimos (entidade, valor_original, saldo_devedor) VALUES (%s, %s, %s)", 
                                   (entidade, valor, valor))
            except:
                continue
        conn.commit()
    conn.close()

@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session: return redirect(url_for('tela_login'))
    
    # Tenta rodar a importação se necessário
    try: rodar_importacao_uma_vez()
    except: pass
    
    return render_template('financeiro.html', nome_sócio=session.get('nome_exibicao', 'Sócio'))
