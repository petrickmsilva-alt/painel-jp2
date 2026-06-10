from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from app import get_db_connection
import pandas as pd
import os

bp_financeiro = Blueprint('financeiro', __name__)

@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session: 
        return redirect(url_for('tela_login'))
    
    # IMPORTAÇÃO AUTOMÁTICA SEGURA
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verifica se já importamos algo
    cursor.execute("SELECT COUNT(*) as total FROM financeiro_emprestimos")
    if cursor.fetchone()['total'] == 0:
        # Pega todos os arquivos que terminam com .csv na pasta raiz
        arquivos = [f for f in os.listdir('.') if f.endswith('.csv')]
        
        for nome_arquivo in arquivos:
            try:
                # header=1 pula o título da planilha
                df = pd.read_csv(nome_arquivo, header=1)
                for _, row in df.iterrows():
                    # Insere apenas se houver um valor numérico
                    valor = row.get('Valor Inicial', 0)
                    if pd.notna(valor):
                        cursor.execute("INSERT INTO financeiro_emprestimos (entidade, valor_original, saldo_devedor) VALUES (%s, %s, %s)", 
                                       (nome_arquivo[:20], valor, valor))
                conn.commit()
            except Exception as e:
                print(f"Erro ao processar {nome_arquivo}: {e}")
                
    conn.close()
    return render_template('financeiro.html')
