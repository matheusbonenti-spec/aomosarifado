from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector

app = Flask(__name__)
app.secret_key = 'senai_chave_secreta'

def get_db():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='aomosarifado'
    )
    return conn

def inicializar_banco():
    try:
        conn_setup = mysql.connector.connect(
            host='localhost',
            user='root',
            password=''
        )
        cursor_setup = conn_setup.cursor()
        cursor_setup.execute("CREATE DATABASE IF NOT EXISTS aomosarifado CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor_setup.close()
        conn_setup.close()

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario VARCHAR(50) UNIQUE NOT NULL,
                senha VARCHAR(255) NOT NULL,
                tipo VARCHAR(20) DEFAULT 'padrao'
            )
        """)

        # Adiciona a coluna 'tipo' caso a tabela já existisse sem ela
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN tipo VARCHAR(20) DEFAULT 'padrao'")
        except:
            pass

        # Garante que o utilizador 'admin' existe e é do tipo 'admin'
        cursor.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO usuarios (usuario, senha, tipo) VALUES ('admin', 'admin', 'admin')")
        else:
            cursor.execute("UPDATE usuarios SET tipo = 'admin' WHERE usuario = 'admin'")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                categoria VARCHAR(50),
                quantidade INT NOT NULL DEFAULT 0,
                imagem_url TEXT,
                descricao TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                produto_id INT,
                usuario_id INT,
                quantidade_retirada INT,
                data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao inicializar banco: {e}")

inicializar_banco()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        senha = request.form['senha'].strip()

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE usuario = %s AND senha = %s", (usuario, senha))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['usuario'] = user['usuario']
            session['tipo'] = user.get('tipo', 'padrao')
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('estoque'))
        else:
            flash('Usuário ou senha incorretos.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sessão encerrada com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/estoque')
@login_required
def estoque():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produtos ORDER BY nome ASC")
    produtos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('estoque.html', produtos=produtos)

@app.route('/produtos/cadastrar', methods=['GET', 'POST'])
@login_required
def cadastrar_produto():
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        categoria = request.form.get('categoria', '').strip()
        quantidade = int(request.form['quantidade'])
        imagem_url = request.form.get('imagem_url', '').strip()
        descricao = request.form.get('descricao', '').strip()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO produtos (nome, categoria, quantidade, imagem_url, descricao) VALUES (%s, %s, %s, %s, %s)",
            (nome, categoria, quantidade, imagem_url, descricao)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash('Produto cadastrado com sucesso!', 'success')
        return redirect(url_for('estoque'))

    return render_template('cadastrar_produto.html')

@app.route('/produtos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_produto(id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        acao = request.form.get('acao')

        if acao == 'atualizar':
            nome = request.form['nome'].strip()
            categoria = request.form.get('categoria', '').strip()
            imagem_url = request.form['imagem_url'].strip()
            descricao = request.form['descricao'].strip()
            quantidade = int(request.form['quantidade'])

            cursor.execute(
                "UPDATE produtos SET nome = %s, categoria = %s, imagem_url = %s, descricao = %s, quantidade = %s WHERE id = %s",
                (nome, categoria, imagem_url, descricao, quantidade, id)
            )
            conn.commit()
            flash('Informações atualizadas com sucesso!', 'success')

        elif acao == 'movimentar':
            tipo_movimento = request.form.get('tipo_movimento')
            qtd = int(request.form['qtd_movimento'])

            cursor.execute("SELECT quantidade FROM produtos WHERE id = %s", (id,))
            prod = cursor.fetchone()

            if prod:
                if tipo_movimento == 'adicionar':
                    nova_qtd = prod['quantidade'] + qtd
                    cursor.execute("UPDATE produtos SET quantidade = %s WHERE id = %s", (nova_qtd, id))
                    conn.commit()
                    flash(f'{qtd} unidade(s) adicionada(s) ao estoque.', 'success')

                elif tipo_movimento == 'retirar':
                    if prod['quantidade'] >= qtd:
                        nova_qtd = prod['quantidade'] - qtd
                        cursor.execute("UPDATE produtos SET quantidade = %s WHERE id = %s", (nova_qtd, id))
                        cursor.execute(
                            "INSERT INTO movimentacoes (produto_id, usuario_id, quantidade_retirada) VALUES (%s, %s, %s)",
                            (id, session['user_id'], qtd)
                        )
                        conn.commit()
                        flash(f'Retirada de {qtd} unidade(s) registrada.', 'success')
                    else:
                        flash('Quantidade indisponível em estoque.', 'danger')

        elif acao == 'excluir':
            cursor.execute("DELETE FROM produtos WHERE id = %s", (id,))
            conn.commit()
            flash('Produto removido.', 'success')
            cursor.close()
            conn.close()
            return redirect(url_for('estoque'))

        cursor.close()
        conn.close()
        return redirect(url_for('estoque'))

    cursor.execute("SELECT * FROM produtos WHERE id = %s", (id,))
    produto = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('editar_produto.html', produto=produto)

@app.route('/historico')
@login_required
def historico():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT m.*, p.nome AS produto_nome, u.usuario AS usuario_nome
        FROM movimentacoes m
        JOIN produtos p ON m.produto_id = p.id
        JOIN usuarios u ON m.usuario_id = u.id
        ORDER BY m.data_movimentacao DESC
    """)
    movimentacoes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('historico.html', movimentacoes=movimentacoes)

@app.route('/relatorio')
@login_required
def imprimir_relatorio():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produtos ORDER BY nome ASC")
    produtos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('relatorio.html', produtos=produtos)

@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
def usuarios():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        senha = request.form['senha'].strip()
        tipo = request.form.get('tipo', 'padrao')

        try:
            cursor.execute("INSERT INTO usuarios (usuario, senha, tipo) VALUES (%s, %s, %s)", (usuario, senha, tipo))
            conn.commit()
            flash('Usuário cadastrado com sucesso!', 'success')
        except Exception as e:
            flash('Erro ao cadastrar usuário. O nome de usuário já pode existir.', 'danger')

    cursor.execute("SELECT id, usuario, tipo FROM usuarios ORDER BY usuario ASC")
    lista_usuarios = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('usuarios.html', usuarios=lista_usuarios)

@app.route('/usuarios/deletar/<int:id>', methods=['POST'])
@login_required
def deletar_usuario(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Usuário removido.', 'success')
    return redirect(url_for('usuarios'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)