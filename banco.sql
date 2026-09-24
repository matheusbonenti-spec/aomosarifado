CREATE DATABASE IF NOT EXISTS almoxarifado_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE almoxarifado_db;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    e_admin BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    categoria VARCHAR(50) NOT NULL DEFAULT 'Ferramentas',
    imagem_url TEXT,
    descricao TEXT,
    quantidade INT NOT NULL DEFAULT 0
);

-- Insere o administrador padrão (usuario: admin | senha: admin123)
INSERT INTO usuarios (nome, usuario, senha, e_admin)
SELECT 'Administrador SENAI', 'admin', 'scrypt:32768:8:1$m9g52J4o8d4K$5dbbfcb6e74b122dd70df83eb2e5d95e2df40bbf9b2e8bfbc5ecf235941c6183a31c50e410f9e9cf2efb2512fefc2a937a0980590a2ffbf296d38e3a2e0a2948', TRUE
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE usuario = 'admin');

-- Preenche a categoria de produtos antigos já existentes no banco
UPDATE produtos SET categoria = 'Ferramentas' WHERE categoria IS NULL OR categoria = '';