import pandas as pd
import pymysql
import os

# 1. Configurações do Banco (Igual ao que você usa no app.py)
DB_CONFIG = {
    'host': os.environ.get("DB_HOST", "localhost"),
    'user': os.environ.get("DB_USER"),
    'password': os.environ.get("DB_PASSWORD"),
    'database': os.environ.get("DB_NAME")
}

def importar_todos():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Lista de arquivos para importar
    arquivos = [f for f in os.listdir('.') if f.endswith('.csv')]
    
    for arquivo in arquivos:
        print(f"Processando: {arquivo}...")
        # O header=1 ignora a primeira linha vazia/título do Excel
        df = pd.read_csv(arquivo, header=1) 
        
        # Limpeza simples: pega só as colunas que importam
        # (Você pode ajustar os nomes das colunas conforme sua planilha)
        for _, row in df.iterrows():
            try:
                # Exemplo: Inserindo na tabela financeiro_emprestimos
                cursor.execute("""
                    INSERT INTO financeiro_emprestimos (entidade, valor_original, saldo_devedor)
                    VALUES (%s, %s, %s)
                """, (arquivo, row.get('Valor Inicial', 0), row.get('Valor Final', 0)))
            except Exception as e:
                print(f"Erro na linha: {e}")
    
    conn.commit()
    conn.close()
    print("Importação concluída com sucesso!")

if __name__ == "__main__":
    importar_todos()
