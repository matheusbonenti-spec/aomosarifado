from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'chave_secreta_almoxarifado_senai'

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'almoxarifado_db'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    """Inicializa as tabelas do banco de dados e cria o usuário admin padrão caso não existam."""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                usuario VARCHAR(50) NOT NULL UNIQUE,
                senha VARCHAR(255) NOT NULL,
                e_admin BOOLEAN NOT NULL DEFAULT FALSE
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                categoria VARCHAR(50) NOT NULL DEFAULT 'Ferramentas',
                imagem_url TEXT,
                descricao TEXT,
                quantidade INT NOT NULL DEFAULT 0
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                produto_id INT NOT NULL,
                usuario_id INT NOT NULL,
                quantidade_retirada INT NOT NULL,
                data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            );
        """)

        cursor.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
        admin_existe = cursor.fetchone()

        if not admin_existe:
            senha_hash = generate_password_hash('admin123')
            cursor.execute(
                "INSERT INTO usuarios (nome, usuario, senha, e_admin) VALUES (%s, %s, %s, %s)",
                ('Administrador SENAI', 'admin', senha_hash, True)
            )
            print("=> Usuário administrador ('admin' / 'admin123') criado com sucesso!")

        conn.commit()
        cursor.close()
        conn.close()
        print("=> Banco de dados verificado e atualizado com sucesso.")
    except Exception as e:
        print(f"=> Erro ao inicializar o banco de dados: {e}")

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

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@app.route('/estoque')
@login_required
def estoque():
    busca = request.args.get('busca', '').strip()
    categoria_filtro = request.args.get('categoria', '').strip()
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM produtos WHERE 1=1"
    params = []

    if categoria_filtro:
        query += " AND categoria = %s"
        params.append(categoria_filtro)

    if busca:
        if busca.isdigit():
            query += " AND id = %s"
            params.append(int(busca))
        else:
            query += " AND nome LIKE %s"
            params.append(f"%{busca}%")

    query += " ORDER BY id DESC"
    cursor.execute(query, tuple(params))
    produtos = cursor.fetchall()

    cursor.close()
    conn.close()

    categorias_disponiveis = [
        "Geral",
        "Elétrica",
        "Eletrônica e Automação",
        "Mecânica",
        "Pneumática e Hidráulica",
        "Ferramentas",
        "Ferramentas de Corte",
        "Instrumentos de Medição",
        "Fixação (Parafusos, Pregos e Porcas)",
        "Lubrificação e Óleos",
        "EPIs e Segurança",
        "Solda e Consumíveis",
        "Acabamento e Pintura",
        "Limpeza e Organização"
    ]

    return render_template(
        'estoque.html',
        produtos=produtos,
        busca=busca,
        categoria_filtro=categoria_filtro,
        categorias=categorias_disponiveis
    )

@app.route('/historico')
@login_required
def historico():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT m.id, p.nome AS produto_nome, p.categoria, u.nome AS usuario_nome, m.quantidade_retirada, m.data_hora
        FROM movimentacoes m
        JOIN produtos p ON m.produto_id = p.id
        JOIN usuarios u ON m.usuario_id = u.id
        ORDER BY m.data_hora DESC
    """
    cursor.execute(query)
    movimentacoes = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('historico.html', movimentacoes=movimentacoes)

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

@app.route('/produtos/novo', methods=['GET', 'POST'])
@login_required
def cadastrar_produto():
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        categoria = request.form.get('categoria', '').strip()
        imagem_url = request.form['imagem_url'].strip()
        descricao = request.form['descricao'].strip()
        quantidade = int(request.form['quantidade'])

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO produtos (nome, categoria, imagem_url, descricao, quantidade) VALUES (%s, %s, %s, %s, %s)",
            (nome, categoria, imagem_url, descricao, quantidade)
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
            flash('Produto atualizado!', 'success')

        elif acao == 'dar_baixa':
            qtd_baixa = int(request.form['qtd_baixa'])
            cursor.execute("SELECT quantidade FROM produtos WHERE id = %s", (id,))
            prod = cursor.fetchone()

            if prod and prod['quantidade'] >= qtd_baixa:
                nova_qtd = prod['quantidade'] - qtd_baixa
                cursor.execute("UPDATE produtos SET quantidade = %s WHERE id = %s", (nova_qtd, id))
                cursor.execute(
                    "INSERT INTO movimentacoes (produto_id, usuario_id, quantidade_retirada) VALUES (%s, %s, %s)",
                    (id, session['user_id'], qtd_baixa)
                )
                conn.commit()
                flash(f'Baixa de {qtd_baixa} unidade(s) registrada no histórico!', 'success')
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

@app.route('/relatorio/imprimir')
@login_required
def imprimir_relatorio():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produtos ORDER BY categoria ASC, nome ASC")
    produtos = cursor.fetchall()
    cursor.close()
    conn.close()

    total_produtos = len(produtos)
    total_itens = sum(p['quantidade'] for p in produtos)
    itens_baixo = sum(1 for p in produtos if p['quantidade'] < 5)
    data_atual = datetime.now().strftime('%d/%m/%Y às %H:%M')

    return render_template(
        'relatorio.html',
        produtos=produtos,
        total_produtos=total_produtos,
        total_itens=total_itens,
        itens_baixo=itens_baixo,
        data_atual=data_atual
    )

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)