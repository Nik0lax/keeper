CREATE INDEX idx_itens_nome ON itens(nome);

CREATE INDEX idx_localizacoes_nome ON localizacoes(nome);

CREATE INDEX idx_users_username ON users(username);

CREATE TABLE estoque (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL,
    quantidade INTEGER NOT NULL DEFAULT 0,
    UNIQUE(nome, tipo) -- evita duplicar o mesmo item
);

CREATE TABLE itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')), descricao TEXT,
    UNIQUE(nome, tipo)
);

CREATE TABLE localizacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE movimentacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL,
    quantidade INTEGER NOT NULL,
    movimento TEXT CHECK(movimento IN ('entrada','saida')) NOT NULL,
    usuario TEXT NOT NULL,
    datahora TEXT NOT NULL DEFAULT (datetime('now','localtime'))
, "localizacao TEXT NOT NULL", localizacao TEXT);

CREATE TABLE sqlite_sequence(name,seq);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'operator',
    created_at TEXT DEFAULT (datetime('now'))
, first_login INTEGER DEFAULT 1);

INSERT INTO users (id, username, password_hash, role, created_at, first_login) VALUES (1, 'admin', 'pbkdf2:sha256:260000$fYzpU48p$3fb0e89ef33323f8f707a0a88209c4c92ba9356b36c843bd306ff40f41f3de9a', 'admin', '2025-10-16 12:41:09', 1);

