from flask import Blueprint, render_template, session, redirect, url_for
from app import get_db_connection

bp_financeiro = Blueprint('financeiro', __name__)

@bp_financeiro.route('/financeiro')
def pagina_financeiro():
    if 'usuario_logado' not in session: 
        return redirect(url_for('tela_login'))
    
    return render_template('financeiro.html', nome_sócio=session.get('nome_exibicao', 'Sócio'))
