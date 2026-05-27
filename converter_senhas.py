import sqlite3
import os
from werkzeug.security import generate_password_hash

# Define o caminho para a pasta 'instance' onde o Flask guarda o banco
db_path = os.path.join('instance', 'banco_painel.db')

# Se não estiver na pasta instance, tenta na pasta raiz
if not os.path.exists(db_path):
    db_path = 'banco_painel.db'

def converter_senhas():
    print(f"Conectando ao banco em: {db_path}")
    conexao = sqlite3.connect(db_path)
    cursor = conexao.cursor()
    
    cursor.execute("SELECT usuario, senha FROM usuarios")
    usuarios = cursor.fetchall()
    
    for u, s in usuarios:
        # Se a senha não começar com 'pbkdf2', ela ainda não é um hash
        if not s.startswith("pbkdf2:"):
            novo_hash = generate_password_hash(s)
            cursor.execute("UPDATE usuarios SET senha = ? WHERE usuario = ?", (novo_hash, u))
            print(f"Sucesso: Senha do usuário '{u}' convertida.")
        else:
            print(f"Aviso: Usuário '{u}' já possui senha segura.")
            
    conexao.commit()
    conexao.close()
    print("\nProcesso finalizado!")

if __name__ == "__main__":
    converter_senhas()