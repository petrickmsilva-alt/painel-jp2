from flask import Blueprint, render_template, session, redirect, url_for
from app import get_db_connection
import pandas as pd
import os

bp_financeiro = Blueprint('financeiro', __name__)

@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session: 
        return redirect(url_for('tela_login'))
    
    # Lista arquivos que terminam com .csv OU .xlsx
    arquivos = [f for f in os.listdir('.') if f.endswith(('.csv', '.xlsx'))]
    
    # DEBUG: Vamos ver no log do Render o que ele achou
    print(f"DEBUG_PETRICK: Arquivos encontrados: {arquivos}")
    
    return render_template('financeiro.html', nome_sócio=session.get('nome_exibicao', 'Sócio'))
