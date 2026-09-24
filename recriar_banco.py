import mysql.connector

# Conecta ao MySQL
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password=''  # Coloque sua senha aqui se houver
)
cursor = conn.cursor()

# Deleta a base antiga desatualizada e cria uma nova
cursor.execute("DROP DATABASE IF EXISTS almoxarifado_db")
cursor.execute("CREATE DATABASE almoxarifado_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
cursor.execute("USE almoxarifado_db")

# Lê o seu arquivo banco.sql e executa os comandos
with open('banco.sql', 'r', encoding='utf-8') as f:
    comandos = f.read().split(';')
    for comando in comandos:
        if comando.strip():
            cursor.execute(comando)

conn.commit()
cursor.close()
conn.close()
print("Banco de dados atualizado com sucesso!")