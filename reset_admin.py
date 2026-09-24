import mysql.connector
from werkzeug.security import generate_password_hash

# Conecta ao banco de dados
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='almoxarifado_db'
)
cursor = conn.cursor()

# Gera o hash exato para o seu ambiente
senha_hash = generate_password_hash('admin123')

# Verifica se o admin existe
cursor.execute("SELECT id FROM usuarios WHERE usuario = 'admin'")
user = cursor.fetchone()

if user:
    cursor.execute("UPDATE usuarios SET senha = %s WHERE usuario = 'admin'", (senha_hash,))
    print("✓ Senha do usuário 'admin' atualizada com sucesso para 'admin123'!")
else:
    cursor.execute(
        "INSERT INTO usuarios (nome, usuario, senha, e_admin) VALUES (%s, %s, %s, %s)",
        ('Administrador SENAI', 'admin', senha_hash, True)
    )
    print("✓ Usuário 'admin' criado com sucesso com a senha 'admin123'!")

conn.commit()
cursor.close()
conn.close()