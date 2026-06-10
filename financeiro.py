from flask import Blueprint, render_template, session, redirect, url_for
from app import get_db_connection
import pandas as pd
import os

bp_financeiro = Blueprint('financeiro', __name__)

@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session: 
        return redirect(url_for('tela_login'))
    
    # DEBUG: Vamos ver o que o servidor enxerga
    arquivos_na_pasta = os.listdir('.')
    print(f"DEBUG - Arquivos encontrados na pasta: {arquivos_na_pasta}")
    
    return render_template('financeiro.html', nome_sócio=session.get('nome_exibicao', 'Sócio'))
