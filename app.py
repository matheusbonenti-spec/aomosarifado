from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'chave_secreta_almoxarifado_senai'

# Configuração de Conexão com o Banco de Dados
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Insira a senha do seu MySQL, se houver
    'database': 'almoxarifado_db'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# Decoradores de Proteção de Rota
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Faça login para acessar esta página.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('e_admin'):
            flash('Acesso restrito apenas para Administradores.', 'danger')
            return redirect(url_for('estoque'))
        return f(*args, **kwargs)
    return decorated_function

# Rota: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        senha = request.form['senha']

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (usuario,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['senha'], senha):
            session['user_id'] = user['id']
            session['nome'] = user['nome']
            session['usuario'] = user['usuario']
            session['e_admin'] = bool(user['e_admin'])
            return redirect(url_for('estoque'))
        else:
            flash('Usuário ou senha incorretos. Tente novamente.', 'danger')

    return render_template('login.html')

# Rota: Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))

# Rota: Estoque / Busca
@app.route('/')
@app.route('/estoque')
@login_required
def estoque():
    busca = request.args.get('busca', '').strip()
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if busca:
        if busca.isdigit():
            query = "SELECT * FROM produtos WHERE id = %s ORDER BY id DESC"
            cursor.execute(query, (int(busca),))
        else:
            query = "SELECT * FROM produtos WHERE nome LIKE %s ORDER BY id DESC"
            cursor.execute(query, (f"%{busca}%",))
    else:
        cursor.execute("SELECT * FROM produtos ORDER BY id DESC")

    produtos = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('estoque.html', produtos=produtos, busca=busca)

# Rota: Gestão de Usuários (Apenas Admin)
@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
@admin_required
def usuarios():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        acao = request.form.get('acao')

        if acao == 'cadastrar':
            nome = request.form['nome'].strip()
            usuario = request.form['usuario'].strip()
            senha = request.form['senha']
            e_admin = True if request.form.get('e_admin') else False

            hash_senha = generate_password_hash(senha)
            try:
                cursor.execute(
                    "INSERT INTO usuarios (nome, usuario, senha, e_admin) VALUES (%s, %s, %s, %s)",
                    (nome, usuario, hash_senha, e_admin)
                )
                conn.commit()
                flash('Novo usuário cadastrado com sucesso!', 'success')
            except mysql.connector.IntegrityError:
                flash('Nome de usuário já existe. Escolha outro.', 'danger')

        elif acao == 'editar':
            user_id = request.form['user_id']
            nome = request.form['nome'].strip()
            nova_senha = request.form['nova_senha']

            if nova_senha:
                hash_senha = generate_password_hash(nova_senha)
                cursor.execute("UPDATE usuarios SET nome = %s, senha = %s WHERE id = %s", (nome, hash_senha, user_id))
            else:
                cursor.execute("UPDATE usuarios SET nome = %s WHERE id = %s", (nome, user_id))
            
            conn.commit()
            flash('Usuário atualizado com sucesso!', 'success')

    cursor.execute("SELECT id, nome, usuario, e_admin FROM usuarios ORDER BY id DESC")
    lista_usuarios = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('usuarios.html', usuarios=lista_usuarios)

# Rota: Excluir Usuário (Apenas Admin)
@app.route('/usuarios/deletar/<int:id>', methods=['POST'])
@login_required
@admin_required
def deletar_usuario(id):
    if id == session['user_id']:
        flash('Você não pode excluir sua própria conta de administrador!', 'danger')
        return redirect(url_for('usuarios'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Usuário removido com sucesso.', 'success')
    return redirect(url_for('usuarios'))

# Rota: Cadastrar Produto
@app.route('/produtos/novo', methods=['GET', 'POST'])
@login_required
def cadastrar_produto():
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        imagem_url = request.form['imagem_url'].strip()
        descricao = request.form['descricao'].strip()
        quantidade = int(request.form['quantidade'])

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO produtos (nome, imagem_url, descricao, quantidade) VALUES (%s, %s, %s, %s)",
            (nome, imagem_url, descricao, quantidade)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash('Produto cadastrado com sucesso!', 'success')
        return redirect(url_for('estoque'))

    return render_template('cadastrar_produto.html')

# Rota: Editar / Dar Baixa / Excluir Produto
@app.route('/produtos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_produto(id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        acao = request.form.get('acao')

        if acao == 'atualizar':
            nome = request.form['nome'].strip()
            imagem_url = request.form['imagem_url'].strip()
            descricao = request.form['descricao'].strip()
            quantidade = int(request.form['quantidade'])

            cursor.execute(
                "UPDATE produtos SET nome = %s, imagem_url = %s, descricao = %s, quantidade = %s WHERE id = %s",
                (nome, imagem_url, descricao, quantidade, id)
            )
            conn.commit()
            flash('Produto atualizado!', 'success')

        elif acao == 'dar_baixa':
            qtd_baixa = int(request.form['qtd_baixa'])
            cursor.execute("SELECT quantidade FROM produtos WHERE id = %s", (id,))
            prod = cursor.fetchone()

            if prod and prod['quantidade'] >= qtd_baixa:
                nova_qtd = prod['quantidade'] - qtd_baixa
                cursor.execute("UPDATE produtos SET quantidade = %s WHERE id = %s", (nova_qtd, id))
                conn.commit()
                flash(f'Baixa de {qtd_baixa} unidade(s) realizada!', 'success')
            else:
                flash('Quantidade para baixa é superior ao estoque disponível.', 'danger')

        elif acao == 'excluir':
            cursor.execute("DELETE FROM produtos WHERE id = %s", (id,))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Produto removido do estoque.', 'success')
            return redirect(url_for('estoque'))

        cursor.close()
        conn.close()
        return redirect(url_for('estoque'))

    cursor.execute("SELECT * FROM produtos WHERE id = %s", (id,))
    produto = cursor.fetchone()
    cursor.close()
    conn.close()

    if not produto:
        flash('Produto não encontrado.', 'danger')
        return redirect(url_for('estoque'))

    return render_template('editar_produto.html', produto=produto)

if __name__ == '__main__':
    app.run(debug=True, port=5001)