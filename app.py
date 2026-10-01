import os
import uuid
from functools import wraps
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'chave_secreta_almoxarifado'

# Função para conectar ao MySQL
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="aomosarifado"
    )

# --- CONFIGURAÇÃO DE UPLOAD DE IMAGENS DE PERFIL ---
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'perfis')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Cria a pasta de uploads se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def salvar_foto(file):
    if file and allowed_file(file.filename):
        extencao = file.filename.rsplit('.', 1)[1].lower()
        nome_unico = f"{uuid.uuid4().hex}.{extencao}"
        caminho_completo = os.path.join(app.config['UPLOAD_FOLDER'], nome_unico)
        file.save(caminho_completo)
        return nome_unico
    return None

def get_db():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='aomosarifado'
    )

def inicializar_banco():
    try:
        conn_setup = mysql.connector.connect(host='localhost', user='root', password='')
        cursor_setup = conn_setup.cursor()
        cursor_setup.execute("CREATE DATABASE IF NOT EXISTS aomosarifado CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor_setup.close()
        conn_setup.close()

        conn = get_db()
        cursor = conn.cursor()

        # Tabela de Usuários com foto_perfil
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario VARCHAR(50) UNIQUE NOT NULL,
                senha VARCHAR(255) NOT NULL,
                tipo VARCHAR(20) DEFAULT 'padrao',
                foto_perfil VARCHAR(255) DEFAULT 'default_avatar.png'
            )
        """)

        # Tenta adicionar a coluna foto_perfil caso a tabela já existisse antes
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN foto_perfil VARCHAR(255) DEFAULT 'default_avatar.png'")
        except:
            pass

        # Tabela de Produtos
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

        # Tabela de Movimentações
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                produto_id INT,
                usuario_id INT,
                quantidade_retirada INT,
                data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE SET NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
        """)

        # Usuário admin padrão
        cursor.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
        if not cursor.fetchone():
            senha_hash = generate_password_hash('admin')
            cursor.execute("INSERT INTO usuarios (usuario, senha, tipo, foto_perfil) VALUES ('admin', %s, 'admin', 'default_avatar.png')", (senha_hash,))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao inicializar banco: {e}")

inicializar_banco()

# --- DECORADORES ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('tipo') != 'admin':
            flash('Acesso negado! Apenas administradores têm permissão.', 'danger')
            return redirect(url_for('estoque'))
        return f(*args, **kwargs)
    return decorated_function

# --- AUTENTICAÇÃO ---

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
        cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (usuario,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and (check_password_hash(user['senha'], senha) or user['senha'] == senha):
            session['user_id'] = user['id']
            session['usuario'] = user['usuario']
            session['tipo'] = user.get('tipo', 'padrao')
            session['foto_perfil'] = user.get('foto_perfil') or 'default_avatar.png'
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

# --- PERFIL DO USUÁRIO LOGADO ---

@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha', '').strip()
        foto_file = request.files.get('foto_perfil')

        if foto_file and foto_file.filename != '':
            nome_foto = salvar_foto(foto_file)
            if nome_foto:
                cursor.execute("UPDATE usuarios SET foto_perfil = %s WHERE id = %s", (nome_foto, session['user_id']))
                session['foto_perfil'] = nome_foto

        if nova_senha:
            senha_hash = generate_password_hash(nova_senha)
            cursor.execute("UPDATE usuarios SET senha = %s WHERE id = %s", (senha_hash, session['user_id']))

        conn.commit()
        flash('Perfil atualizado com sucesso!', 'success')

    cursor.execute("SELECT id, usuario, tipo, foto_perfil FROM usuarios WHERE id = %s", (session['user_id'],))
    dados_usuario = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('perfil.html', usuario_item=dados_usuario)

# --- ESTOQUE E HISTÓRICO ---

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
            if session.get('tipo') != 'admin':
                flash('Apenas administradores podem excluir produtos.', 'danger')
            else:
                cursor.execute("DELETE FROM produtos WHERE id = %s", (id,))
                conn.commit()
                flash('Produto removido do sistema.', 'success')
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
        SELECT m.*, COALESCE(p.nome, 'Produto Removido') AS produto_nome, 
               COALESCE(u.usuario, 'Usuário Removido') AS usuario_nome,
               COALESCE(u.foto_perfil, 'default_avatar.png') AS usuario_foto
        FROM movimentacoes m
        LEFT JOIN produtos p ON m.produto_id = p.id
        LEFT JOIN usuarios u ON m.usuario_id = u.id
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

# --- GERENCIAMENTO DE USUÁRIOS (ADMIN) ---

@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
@admin_required
def usuarios():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        senha = request.form['senha'].strip()
        tipo = request.form.get('tipo', 'padrao')
        foto_file = request.files.get('foto_perfil')

        nome_foto = salvar_foto(foto_file) or 'default_avatar.png'
        senha_hash = generate_password_hash(senha)

        try:
            cursor.execute("INSERT INTO usuarios (usuario, senha, tipo, foto_perfil) VALUES (%s, %s, %s, %s)",
                           (usuario, senha_hash, tipo, nome_foto))
            conn.commit()
            flash('Usuário cadastrado com sucesso!', 'success')
        except Exception as e:
            flash('Erro ao cadastrar usuário. Nome de usuário já existe.', 'danger')

    cursor.execute("SELECT id, usuario, tipo, foto_perfil FROM usuarios ORDER BY usuario ASC")
    lista_usuarios = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('usuarios.html', usuarios=lista_usuarios)

@app.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        tipo = request.form.get('tipo', 'padrao')
        nova_senha = request.form.get('nova_senha', '').strip()
        foto_file = request.files.get('foto_perfil')

        if foto_file and foto_file.filename != '':
            nome_foto = salvar_foto(foto_file)
            if nome_foto:
                cursor.execute("UPDATE usuarios SET foto_perfil = %s WHERE id = %s", (nome_foto, id))

        if nova_senha:
            senha_hash = generate_password_hash(nova_senha)
            cursor.execute("UPDATE usuarios SET tipo = %s, senha = %s WHERE id = %s", (tipo, senha_hash, id))
        else:
            cursor.execute("UPDATE usuarios SET tipo = %s WHERE id = %s", (tipo, id))

        conn.commit()
        cursor.close()
        conn.close()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('usuarios'))

    cursor.execute("SELECT id, usuario, tipo, foto_perfil FROM usuarios WHERE id = %s", (id,))
    usuario_item = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('editar_usuario.html', usuario_item=usuario_item)

@app.route('/usuarios/deletar/<int:id>', methods=['POST'])
@login_required
@admin_required
def deletar_usuario(id):
    if id == session.get('user_id'):
        flash('Não é possível remover a sua própria conta enquanto estiver ligado.', 'danger')
        return redirect(url_for('usuarios'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Usuário removido com sucesso.', 'success')
    return redirect(url_for('usuarios'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)