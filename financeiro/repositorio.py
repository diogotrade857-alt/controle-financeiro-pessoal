"""Camada de persistência: acesso ao SQLite (RNF03).

Toda a SQL fica isolada aqui; o restante do sistema só conhece objetos de domínio.
Regra de isolamento entre usuários: toda consulta filtra por `usuario_id IS ?`.
`usuario_id=None` significa "registros sem dono" (dados legados da Entrega 2).
"""
import sqlite3
from datetime import date

from financeiro.banco import Banco
from financeiro.excecoes import (ArquivoError, MetaNaoEncontradaError,
                                 TransacaoNaoEncontradaError, ValidacaoError)
from financeiro.modelos import Meta, criar_transacao


class RepositorioTransacoes:
    """Acesso ao SQLite para transações; toda consulta é filtrada por usuário."""
    def __init__(self, origem="financeiro.db"):
        # Aceita um caminho de arquivo ou um objeto Banco já aberto.
        self._banco = origem if isinstance(origem, Banco) else Banco(origem)

    @property
    def banco(self):
        return self._banco

    @property
    def _conn(self):
        return self._banco.conn

    def fechar(self):
        """Fecha a conexão com o banco."""
        self._banco.fechar()

    @staticmethod
    def _para_objeto(linha):
        return criar_transacao(
            linha["tipo"], date.fromisoformat(linha["data"]), linha["valor"],
            linha["categoria"], linha["descricao"], id=linha["id"],
        )

    @staticmethod
    def _filtro(usuario_id, tipo=None, inicio=None, fim=None):
        condicoes, params = ["usuario_id IS ?"], [usuario_id]
        if tipo:
            condicoes.append("tipo = ?")
            params.append(tipo)
        if inicio:
            condicoes.append("data >= ?")
            params.append(inicio.isoformat())
        if fim:
            condicoes.append("data <= ?")
            params.append(fim.isoformat())
        return " WHERE " + " AND ".join(condicoes), params

    # ---------- CRUD ----------
    def adicionar(self, t, usuario_id=None):
        """Grava a transação, define o ID gerado pelo banco e a devolve."""
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO transacoes (tipo, data, valor, categoria, descricao, usuario_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (t.tipo(), t.data.isoformat(), t.valor, t.categoria, t.descricao, usuario_id),
            )
        t.atribuir_id(cur.lastrowid)
        return t

    def listar(self, tipo=None, usuario_id=None, inicio=None, fim=None):
        """Lista as transações do usuário, ordenadas por data, com filtros opcionais."""
        where, params = self._filtro(usuario_id, tipo, inicio, fim)
        sql = "SELECT * FROM transacoes" + where + " ORDER BY data, id"
        return [self._para_objeto(l) for l in self._conn.execute(sql, params)]

    def buscar(self, id_, usuario_id=None):
        """Busca uma transação pelo ID; lança TransacaoNaoEncontradaError se não existir."""
        linha = self._conn.execute(
            "SELECT * FROM transacoes WHERE id = ? AND usuario_id IS ?",
            (id_, usuario_id)).fetchone()
        if linha is None:
            raise TransacaoNaoEncontradaError(f"Transação ID {id_} não encontrada.")
        return self._para_objeto(linha)

    def atualizar(self, t, usuario_id=None):
        """Grava no banco as alterações de uma transação já existente."""
        with self._conn:
            cur = self._conn.execute(
                "UPDATE transacoes SET data=?, valor=?, categoria=?, descricao=? "
                "WHERE id=? AND usuario_id IS ?",
                (t.data.isoformat(), t.valor, t.categoria, t.descricao, t.id, usuario_id),
            )
        if cur.rowcount == 0:
            raise TransacaoNaoEncontradaError(f"Transação ID {t.id} não encontrada.")

    def remover(self, id_, usuario_id=None):
        """Remove a transação pelo ID; lança TransacaoNaoEncontradaError se não existir."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM transacoes WHERE id = ? AND usuario_id IS ?", (id_, usuario_id))
        if cur.rowcount == 0:
            raise TransacaoNaoEncontradaError(f"Transação ID {id_} não encontrada.")

    def total_registros(self, usuario_id=None):
        """Quantidade de transações do usuário."""
        return self._conn.execute(
            "SELECT COUNT(*) FROM transacoes WHERE usuario_id IS ?", (usuario_id,)).fetchone()[0]

    # ---------- agregações feitas pelo banco (RF08–RF11) ----------
    def totais_por_tipo(self, usuario_id=None, inicio=None, fim=None):
        """Soma de receitas e despesas, calculada pelo banco."""
        where, params = self._filtro(usuario_id, None, inicio, fim)
        linhas = self._conn.execute(
            "SELECT tipo, SUM(valor) AS total FROM transacoes" + where + " GROUP BY tipo", params)
        totais = {"receita": 0.0, "despesa": 0.0}
        for l in linhas:
            totais[l["tipo"]] = l["total"]
        return totais

    def quantidades_por_tipo(self, usuario_id=None, inicio=None, fim=None):
        """Quantidade de receitas e de despesas, contada pelo banco."""
        where, params = self._filtro(usuario_id, None, inicio, fim)
        linhas = self._conn.execute(
            "SELECT tipo, COUNT(*) AS qtd FROM transacoes" + where + " GROUP BY tipo", params)
        quantidades = {"receita": 0, "despesa": 0}
        for l in linhas:
            quantidades[l["tipo"]] = l["qtd"]
        return quantidades

    def totais_por_categoria(self, tipo, usuario_id=None, inicio=None, fim=None):
        """Soma por categoria de um tipo de transação, calculada pelo banco."""
        where, params = self._filtro(usuario_id, tipo, inicio, fim)
        linhas = self._conn.execute(
            "SELECT categoria, SUM(valor) AS total FROM transacoes" + where +
            " GROUP BY categoria", params)
        return [(l["categoria"], l["total"]) for l in linhas]

    def totais_por_mes(self, ano, usuario_id=None):
        """Soma por mês e tipo de um ano, calculada pelo banco."""
        where, params = self._filtro(usuario_id, None, date(ano, 1, 1), date(ano, 12, 31))
        linhas = self._conn.execute(
            "SELECT substr(data, 1, 7) AS mes, tipo, SUM(valor) AS total FROM transacoes" +
            where + " GROUP BY mes, tipo ORDER BY mes", params)
        return [(l["mes"], l["tipo"], l["total"]) for l in linhas]

    # ---------- migração do sistema anterior (CSV da disciplina de POO) ----------
    def importar_csv(self, caminho, usuario_id=None):
        """Importa o arquivo transacoes_poo.csv (id;tipo;data;valor;categoria;descricao).

        Linhas malformadas são ignoradas e registros idênticos a um já existente
        não são duplicados, então a importação pode ser repetida sem efeitos colaterais.
        Retorna a quantidade de registros efetivamente importados.
        """
        importados = 0
        try:
            with open(caminho, "r", encoding="utf-8-sig") as arquivo:
                for linha in arquivo:
                    campos = linha.strip().split(";")
                    if len(campos) != 6:
                        continue
                    _, tipo, data, valor, categoria, descricao = campos
                    try:
                        t = criar_transacao(tipo, data, valor, categoria, descricao)
                    except ValidacaoError:
                        continue
                    if self._existe_igual(t, usuario_id):
                        continue
                    self.adicionar(t, usuario_id)
                    importados += 1
        except (OSError, UnicodeDecodeError) as erro:
            raise ArquivoError(f"Não foi possível ler '{caminho}': {erro}")
        return importados

    def _existe_igual(self, t, usuario_id=None):
        linha = self._conn.execute(
            "SELECT 1 FROM transacoes WHERE tipo=? AND data=? AND valor=? "
            "AND categoria=? AND descricao=? AND usuario_id IS ? LIMIT 1",
            (t.tipo(), t.data.isoformat(), t.valor, t.categoria, t.descricao, usuario_id),
        ).fetchone()
        return linha is not None


class RepositorioMetas:
    """Acesso ao SQLite para as metas de gasto de cada usuário."""
    def __init__(self, banco):
        self._banco = banco

    @property
    def _conn(self):
        return self._banco.conn

    def listar(self, usuario_id=None):
        """Lista as metas do usuário, em ordem alfabética de categoria."""
        linhas = self._conn.execute(
            "SELECT * FROM metas WHERE usuario_id IS ? ORDER BY categoria", (usuario_id,))
        return [Meta(l["categoria"], l["limite"], id=l["id"]) for l in linhas]

    def adicionar(self, meta, usuario_id=None):
        """Grava uma nova meta; lança ValidacaoError se a categoria já tiver meta."""
        try:
            with self._conn:
                cur = self._conn.execute(
                    "INSERT INTO metas (usuario_id, categoria, limite) VALUES (?, ?, ?)",
                    (usuario_id, meta.categoria, meta.limite))
        except sqlite3.IntegrityError:
            raise ValidacaoError(f"Já existe meta para a categoria '{meta.categoria}'.")
        meta._id = cur.lastrowid
        return meta

    def atualizar(self, meta, usuario_id=None):
        """Grava as alterações de uma meta existente."""
        with self._conn:
            cur = self._conn.execute(
                "UPDATE metas SET categoria=?, limite=? WHERE id=? AND usuario_id IS ?",
                (meta.categoria, meta.limite, meta.id, usuario_id))
        if cur.rowcount == 0:
            raise MetaNaoEncontradaError("Meta não encontrada.")

    def remover(self, id_, usuario_id=None):
        """Remove a meta pelo ID."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM metas WHERE id=? AND usuario_id IS ?", (id_, usuario_id))
        if cur.rowcount == 0:
            raise MetaNaoEncontradaError("Meta não encontrada.")
