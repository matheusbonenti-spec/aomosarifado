-- 1. Criação do Banco de Dados
CREATE DATABASE IF NOT EXISTS aomosarifado 
DEFAULT CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE aomosarifado;

-- 2. Tabela de Usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    perfil VARCHAR(20) NOT NULL DEFAULT 'Padrão',
    foto VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabela de Produtos (Estoque)
CREATE TABLE IF NOT EXISTS produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    quantidade INT NOT NULL DEFAULT 0,
    categoria VARCHAR(50) DEFAULT 'Geral',
    descricao TEXT DEFAULT NULL,
    imagem VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tabela de Histórico de Movimentações
CREATE TABLE IF NOT EXISTS historico (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_nome VARCHAR(100) NOT NULL,
    produto_nome VARCHAR(100) NOT NULL,
    acao VARCHAR(50) NOT NULL, -- Ex: "Adicionou", "Removeu", "Editou"
    quantidade INT NOT NULL,
    data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Inserir um Usuário Administrador Padrão (se ainda não existir)
-- Login: admin | Senha: 123
INSERT IGNORE INTO usuarios (id, nome, usuario, senha, perfil) 
VALUES (1, 'Administrador SENAI', 'admin', '123', 'Administrador');