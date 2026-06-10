import os
import pymysql
import pandas as pd

# Aqui usamos as variáveis que o seu sistema já reconhece
DB_CONFIG = {
    'host': os.environ.get("DB_HOST", "br778.hostgator.com.br"),
    'user': os.environ.get("DB_USER", "brobon39_ibdtec_petrick"),
    'password': os.environ.get("DB_PASSWORD", "FR-R-PH]C@Uj"),
    'database': os.environ.get("DB_NAME", "brobon39_ibdtec_painel"),
    'cursorclass': pymysql.cursors.DictCursor
}

def importar_dados():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        print("Conectado ao banco com sucesso!")
        conn.close()
    except Exception as e:
        print(f"Erro ao conectar: {e}")

if __name__ == "__main__":
    importar_dados()
