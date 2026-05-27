import sqlite3

conexao = sqlite3.connect("banco_painel.db")
cursor = conexao.cursor()

# Comando para listar todas as tabelas do banco
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tabelas = cursor.fetchall()

print("As tabelas encontradas no seu banco são:")
for tabela in tabelas:
    print(tabela[0])

conexao.close()