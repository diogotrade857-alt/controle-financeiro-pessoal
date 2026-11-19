"""Usuários e autenticação (RF01 e RF02)."""
import re
import sqlite3

from financeiro import seguranca
from financeiro.excecoes import AutenticacaoError, ValidacaoError

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SENHA_MINIMA = 6


class Usuario:
    def __init__(self, nome, email, id=None):
        self._id = id
        self.nome = nome
        self.email = email

    @property
    def id(self):
        return self._id

    @property
    def nome(self):
        return self._nome

    @nome.setter
    def nome(self, novo):
        texto = str(novo).strip()
        if not texto:
            raise ValidacaoError("O nome é obrigatório.")
        self._nome = texto

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, novo):
        texto = str(novo).strip().lower()
        if not _EMAIL.match(texto):
            raise ValidacaoError("E-mail inválido.")
        self._email = texto

    def __repr__(self):
        return f"Usuario(id={self.id}, email={self.email!r})"


class RepositorioUsuarios:
    def __init__(self, banco):
        self._banco = banco

    @property
    def _conn(self):
        return self._banco.conn

    def contar(self):
        return self._conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]

    def adicionar(self, usuario, senha_hash):
        """Grava o usuário. O primeiro usuário do banco herda os dados sem dono da Entrega 2."""
        try:
            with self._conn:
                primeiro = self.contar() == 0
                cur = self._conn.execute(
                    "INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)",
                    (usuario.nome, usuario.email, senha_hash))
                if primeiro:
                    for tabela in ("transacoes", "metas"):
                        self._conn.execute(
                            f"UPDATE {tabela} SET usuario_id = ? WHERE usuario_id IS NULL",
                            (cur.lastrowid,))
        except sqlite3.IntegrityError:
            raise ValidacaoError("Já existe um usuário com esse e-mail.")
        usuario._id = cur.lastrowid
        return usuario

    def buscar_por_email(self, email):
        linha = self._conn.execute(
            "SELECT * FROM usuarios WHERE email = ?", (str(email).strip().lower(),)).fetchone()
        if linha is None:
            return None
        return Usuario(linha["nome"], linha["email"], id=linha["id"]), linha["senha_hash"]


class ServicoUsuarios:
    def __init__(self, repositorio_usuarios):
        self._repo = repositorio_usuarios

    def cadastrar(self, nome, email, senha):
        usuario = Usuario(nome, email)           # valida nome e e-mail
        if not isinstance(senha, str) or len(senha) < SENHA_MINIMA:
            raise ValidacaoError(f"A senha deve ter pelo menos {SENHA_MINIMA} caracteres.")
        return self._repo.adicionar(usuario, seguranca.gerar_hash(senha))

    def autenticar(self, email, senha):
        encontrado = self._repo.buscar_por_email(email)
        # Mesma mensagem para e-mail inexistente e senha errada (não revela quais e-mails existem).
        if encontrado is None or not seguranca.verificar(str(senha), encontrado[1]):
            raise AutenticacaoError("E-mail ou senha incorretos.")
        return encontrado[0]

    def total_usuarios(self):
        return self._repo.contar()
