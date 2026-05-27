import sqlite3

def criar_agenda():
    conn = sqlite3.connect('banco_painel.db')
    cursor = conn.cursor()
    
    # Tabela unificada para Eventos e Reuniões
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_item TEXT NOT NULL, -- 'Evento' ou 'Reunião'
            titulo TEXT NOT NULL,
            local TEXT,
            data_inicio DATETIME NOT NULL,
            horario TEXT,
            responsavel TEXT,
            status TEXT,
            observacao TEXT,
            detalhes_extras TEXT -- Para 'Tipo de Reunião' ou 'Projeto'
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Tabela 'agenda' criada com sucesso!")

if __name__ == "__main__":
    criar_agenda()