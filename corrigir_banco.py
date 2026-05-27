import sqlite3

def consertar_tabela():
    conn = sqlite3.connect('banco_painel.db')
    cursor = conn.cursor()
    
    # 1. Criar a nova tabela com caminho_sistema opcional
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS arquivos_painel_novo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_original TEXT NOT NULL,
            caminho_sistema TEXT,
            bloco TEXT NOT NULL,
            categoria TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'arquivo',
            pasta_pai_id INTEGER DEFAULT NULL,
            criado_por TEXT,
            data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Copiar os dados da antiga para a nova (tentando evitar erros de coluna)
    try:
        cursor.execute('''
            INSERT INTO arquivos_painel_novo (id, nome_original, caminho_sistema, bloco, categoria, tipo, pasta_pai_id, criado_por, data_upload)
            SELECT id, nome_original, caminho_sistema, bloco, categoria, tipo, pasta_pai_id, criado_por, data_upload 
            FROM arquivos_painel
        ''')
    except sqlite3.OperationalError:
        print("Aviso: Algumas colunas não existiam na tabela antiga, mas a nova está pronta.")
    
    # 3. Remover a tabela antiga e renomear a nova
    cursor.execute('DROP TABLE arquivos_painel')
    cursor.execute('ALTER TABLE arquivos_painel_novo RENAME TO arquivos_painel')
    
    conn.commit()
    conn.close()
    print("Banco consertado com sucesso!")

if __name__ == "__main__":
    consertar_tabela()