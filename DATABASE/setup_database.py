import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()


connection = mysql.connector.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT', 3306)),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

cursor = connection.cursor()

# Criar database
cursor.execute("CREATE DATABASE IF NOT EXISTS kommo_analytics")
print(" Database 'kommo_analytics' criado/verificado")

# Verificar
cursor.execute("SHOW DATABASES")
databases = cursor.fetchall()
print("\n Databases disponíveis:")
for db in databases:
    print(f"  - {db[0]}")

cursor.close()
connection.close()
print("\n Setup concluído! Agora execute os ETLs.")