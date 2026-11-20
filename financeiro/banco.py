"""Conexão SQLite, criação/migração do esquema e backup/restauração (RF14, RNF03)."""
import os
import sqlite3

from financeiro.excecoes import ArquivoError, BackupError

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    senha_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transacoes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo       TEXT    NOT NULL CHECK (tipo IN ('receita', 'despesa')),
    data       TEXT    NOT NULL,              -- formato ISO (aaaa-mm-dd)
    valor      REAL    NOT NULL CHECK (valor > 0),
    categoria  TEXT    NOT NULL,
    descricao  TEXT    NOT NULL DEFAULT '',
    usuario_id INTEGER REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS metas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    categoria  TEXT NOT NULL,
    limite     REAL NOT NULL CHECK (limite > 0),
    UNIQUE (usuario_id, categoria)
);
"""


class Banco:
    """Conexão com o SQLite: cria o esquema, migra bancos antigos e faz backup e restauração."""
    def __init__(self, caminho="financeiro.db"):
        # ":memory:" cria um banco temporário (usado nos testes automatizados).
        try:
            self.conn = sqlite3.connect(caminho)
        except sqlite3.Error as erro:
            raise ArquivoError(f"Não foi possível abrir o banco '{caminho}': {erro}")
        self.conn.row_factory = sqlite3.Row
        self._preparar()

    def _preparar(self):
        """Cria o esquema e migra bancos da Entrega 2 (sem a coluna usuario_id)."""
        try:
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.executescript(_ESQUEMA)
            colunas = [c["name"] for c in self.conn.execute("PRAGMA table_info(transacoes)")]
            if "usuario_id" not in colunas:
                with self.conn:
                    self.conn.execute(
                        "ALTER TABLE transacoes ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id)")
            with self.conn:
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_transacoes_usuario_data "
                    "ON transacoes (usuario_id, data)")
        except sqlite3.DatabaseError as erro:
            raise ArquivoError(f"O arquivo informado não é um banco válido: {erro}")

    def fechar(self):
        """Fecha a conexão com o banco."""
        self.conn.close()

    # ---------------- RF14: backup e restauração ----------------
    def backup(self, destino):
        """Copia o banco inteiro para 'destino' (usa a API de backup online do SQLite)."""
        if os.path.exists(destino):
            raise BackupError("Já existe um arquivo com esse nome; escolha outro para não sobrescrevê-lo.")
        try:
            copia = sqlite3.connect(destino)
            try:
                self.conn.backup(copia)
            finally:
                copia.close()
        except (sqlite3.Error, OSError) as erro:
            if os.path.exists(destino):
                os.remove(destino)
            raise BackupError(f"Falha ao criar o backup: {erro}")

    def restaurar(self, origem):
        """Substitui TODO o conteúdo do banco atual pelo do arquivo de backup."""
        if not os.path.isfile(origem):
            raise BackupError("Arquivo de backup não encontrado.")
        try:
            fonte = sqlite3.connect(origem)
            try:
                if fonte.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise BackupError("O arquivo de backup está corrompido.")
                tabelas = {l[0] for l in fonte.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'")}
                if "transacoes" not in tabelas:
                    raise BackupError("O arquivo não parece ser um backup deste sistema.")
                fonte.backup(self.conn)
            finally:
                fonte.close()
        except sqlite3.Error as erro:
            raise BackupError(f"Falha ao restaurar o backup: {erro}")
        self._preparar()   # backups antigos (Entrega 2) ganham as tabelas/colunas novas
