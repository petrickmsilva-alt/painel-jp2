import sqlite3

def consertar_usuarios():
    try:
        # Tenta conectar ao banco
        conn = sqlite3.connect('banco_painel.db')
        cursor = conn.cursor()
        
        # Verifica se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios';")
        if not cursor.fetchone():
            print("ERRO: A tabela 'usuarios' não foi encontrada no banco 'banco_painel.db'.")
            return

        # Lista os usuários
        cursor.execute("SELECT id, usuario, nome_exibicao FROM usuarios")
        users = cursor.fetchall()
        
        if not users:
            print("A tabela 'usuarios' está vazia!")
            return

        print("\n--- LISTA DE USUÁRIOS ENCONTRADOS ---")
        for u in users:
            print(f"ID: {u[0]} | Usuário: {u[1]} | Nome Exibição Atual: {u[2]}")
        
        user_id = input("\nDigite o ID do usuário que deseja atualizar: ").strip()
        novo_nome = input("Digite o NOME COMPLETO para exibição: ").strip()
        
        cursor.execute("UPDATE usuarios SET nome_exibicao = ? WHERE id = ?", (novo_nome, user_id))
        conn.commit()
        
        print(f"\nSucesso! Usuário {user_id} atualizado para '{novo_nome}'.")
        conn.close()

    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    consertar_usuarios()