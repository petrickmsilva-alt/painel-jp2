import sqlite3
conexao = sqlite3.connect('banco_de_dados.db') # Certifique-se que o nome do arquivo .db está correto
cursor = conexao.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tabelas = cursor.fetchall()
print("Tabelas encontradas:", tabelas)
conexao.close()