"""Camada de serviço: regras de negócio do controle financeiro.

ControleFinanceiro TEM-UM repositório (composição), está vinculado a UM usuário
(usuario_id) e trabalha apenas com objetos de domínio, sem conhecer SQL nem interface.
"""
import calendar
import csv
from dataclasses import dataclass
from datetime import date

from financeiro.excecoes import (ArquivoError, MetaNaoEncontradaError, ValidacaoError)
from financeiro.modelos import Despesa, Meta, Receita, converter_data
from financeiro.repositorio import RepositorioMetas


@dataclass(frozen=True)
class Saldo:
    """Total de receitas, total de despesas e saldo."""
    receitas: float
    despesas: float

    @property
    def total(self):
        return round(self.receitas - self.despesas, 2)


@dataclass(frozen=True)
class ResumoPeriodo:
    """Receitas, despesas, saldo e quantidade de lançamentos de um período."""
    inicio: object             # date ou None (sem limite)
    fim: object                # date ou None (sem limite)
    receitas: float
    despesas: float
    qtd_receitas: int
    qtd_despesas: int

    @property
    def saldo(self):
        return round(self.receitas - self.despesas, 2)


@dataclass(frozen=True)
class ResumoCategoria:
    """Total e percentual de uma categoria."""
    categoria: str
    total: float
    percentual: float          # fatia da categoria no total do tipo (0 a 100)


@dataclass(frozen=True)
class ResumoMensal:
    """Receitas, despesas e saldo de um mês."""
    mes: str                   # 'aaaa-mm'
    receitas: float
    despesas: float

    @property
    def saldo(self):
        return round(self.receitas - self.despesas, 2)


@dataclass(frozen=True)
class StatusMeta:
    """Situação de uma meta no mês: limite, gasto, percentual e se foi excedida."""
    categoria: str
    limite: float
    gasto: float

    @property
    def percentual(self):
        return round(self.gasto / self.limite * 100, 1)

    @property
    def restante(self):
        return round(self.limite - self.gasto, 2)

    @property
    def excedida(self):
        return self.gasto > self.limite


class ControleFinanceiro:
    """Regras de negócio do sistema para um usuário (camada de serviço)."""
    def __init__(self, repositorio, usuario_id=None, metas=None):
        self._repo = repositorio
        self._uid = usuario_id
        self._metas = metas if metas is not None else RepositorioMetas(repositorio.banco)

    # ---------- período ----------
    @staticmethod
    def _periodo(inicio, fim):
        ini = converter_data(inicio) if inicio not in (None, "") else None
        f = converter_data(fim) if fim not in (None, "") else None
        if ini and f and ini > f:
            raise ValidacaoError("A data inicial não pode ser posterior à data final.")
        return ini, f

    # ---------- RF03 / RF04 ----------
    def registrar_receita(self, data, valor, categoria, descricao=""):
        """Registra uma receita do usuário (RF03)."""
        return self._repo.adicionar(Receita(data, valor, categoria, descricao), self._uid)

    def registrar_despesa(self, data, valor, categoria, descricao=""):
        """Registra uma despesa do usuário (RF04)."""
        return self._repo.adicionar(Despesa(data, valor, categoria, descricao), self._uid)

    # ---------- RF05 / RF11 ----------
    def listar(self, tipo=None, inicio=None, fim=None):
        """Lista as movimentações, com filtro opcional de tipo e período (RF05)."""
        if tipo not in (None, "receita", "despesa"):
            raise ValidacaoError("Tipo deve ser 'receita' ou 'despesa'.")
        ini, f = self._periodo(inicio, fim)
        return self._repo.listar(tipo, self._uid, ini, f)

    def obter(self, id_):
        """Busca uma movimentação do usuário pelo ID."""
        return self._repo.buscar(id_, self._uid)

    # ---------- RF06: só altera os campos informados (None = manter) ----------
    def editar(self, id_, data=None, valor=None, categoria=None, descricao=None):
        """Altera apenas os campos informados de uma movimentação (RF06)."""
        t = self._repo.buscar(id_, self._uid)
        if data is not None:
            t.data = data
        if valor is not None:
            t.valor = valor
        if categoria is not None:
            t.categoria = categoria
        if descricao is not None:
            t.descricao = descricao
        self._repo.atualizar(t, self._uid)   # só chega aqui se todas as validações passaram
        return t

    # ---------- RF07 ----------
    def remover(self, id_):
        """Remove uma movimentação pelo ID (RF07)."""
        self._repo.remover(id_, self._uid)

    # ---------- RF08 ----------
    def calcular_saldo(self, inicio=None, fim=None):
        """Calcula receitas, despesas e saldo, em todo o histórico ou em um período (RF08)."""
        ini, f = self._periodo(inicio, fim)
        totais = self._repo.totais_por_tipo(self._uid, ini, f)
        return Saldo(round(totais["receita"], 2), round(totais["despesa"], 2))

    # ---------- RF09: relatório por período ----------
    def relatorio_por_periodo(self, inicio=None, fim=None):
        """Receitas, despesas, saldo e quantidade de lançamentos entre duas datas (RF09)."""
        ini, f = self._periodo(inicio, fim)
        totais = self._repo.totais_por_tipo(self._uid, ini, f)
        qtds = self._repo.quantidades_por_tipo(self._uid, ini, f)
        return ResumoPeriodo(ini, f, round(totais["receita"], 2), round(totais["despesa"], 2),
                             qtds["receita"], qtds["despesa"])

    # ---------- RF10: relatório por categoria ----------
    def relatorio_por_categoria(self, tipo="despesa", inicio=None, fim=None):
        """Total e percentual de cada categoria, de despesas ou receitas (RF10)."""
        if tipo not in ("receita", "despesa"):
            raise ValidacaoError("Tipo deve ser 'receita' ou 'despesa'.")
        ini, f = self._periodo(inicio, fim)
        somas = self._agrupar_categorias(self._repo.totais_por_categoria(tipo, self._uid, ini, f))
        total_geral = sum(somas.values())
        resumo = [ResumoCategoria(nome, round(v, 2), round(v / total_geral * 100, 1))
                  for nome, v in somas.items()]
        return sorted(resumo, key=lambda r: (-r.total, r.categoria))

    @staticmethod
    def _agrupar_categorias(pares):
        """Une 'Alimentação' e 'alimentação' na mesma categoria (ignora caixa)."""
        nomes, somas = {}, {}
        for nome, total in pares:
            chave = nome.casefold()
            nomes.setdefault(chave, nome)
            somas[chave] = somas.get(chave, 0.0) + total
        return {nomes[c]: v for c, v in somas.items()}

    # ---------- complemento do RF09: resumo mensal ----------
    def relatorio_mensal(self, ano):
        """Receitas, despesas e saldo de cada mês de um ano (complemento do RF09)."""
        try:
            ano = int(ano)
        except (TypeError, ValueError):
            raise ValidacaoError("Ano inválido.")
        if not 1900 <= ano <= 2100:
            raise ValidacaoError("Ano deve estar entre 1900 e 2100.")
        meses = {}
        for mes, tipo, total in self._repo.totais_por_mes(ano, self._uid):
            meses.setdefault(mes, {"receita": 0.0, "despesa": 0.0})[tipo] = total
        return [ResumoMensal(m, round(v["receita"], 2), round(v["despesa"], 2))
                for m, v in sorted(meses.items())]

    # ---------- RF12: metas de gastos por categoria ----------
    def _meta_da_categoria(self, categoria):
        chave = str(categoria).strip().casefold()
        for meta in self._metas.listar(self._uid):
            if meta.categoria.casefold() == chave:
                return meta
        return None

    def definir_meta(self, categoria, limite):
        """Cria a meta da categoria ou, se já existir, atualiza o limite."""
        existente = self._meta_da_categoria(categoria)
        if existente is None:
            return self._metas.adicionar(Meta(categoria, limite), self._uid)
        existente.limite = limite
        self._metas.atualizar(existente, self._uid)
        return existente

    def listar_metas(self):
        """Lista as metas de gasto do usuário (RF11)."""
        return self._metas.listar(self._uid)

    def remover_meta(self, categoria):
        """Remove a meta de uma categoria."""
        meta = self._meta_da_categoria(categoria)
        if meta is None:
            raise MetaNaoEncontradaError(f"Não há meta para a categoria '{categoria}'.")
        self._metas.remover(meta.id, self._uid)

    @staticmethod
    def _limites_do_mes(ano, mes):
        if not 1 <= mes <= 12:
            raise ValidacaoError("Mês deve estar entre 1 e 12.")
        return date(ano, mes, 1), date(ano, mes, calendar.monthrange(ano, mes)[1])

    def status_metas(self, ano, mes):
        """Acompanha o gasto de cada meta em um mês (RF12)."""
        ini, fim = self._limites_do_mes(ano, mes)
        gastos = {c.casefold(): v for c, v in self._agrupar_categorias(
            self._repo.totais_por_categoria("despesa", self._uid, ini, fim)).items()}
        return [StatusMeta(m.categoria, m.limite, round(gastos.get(m.categoria.casefold(), 0.0), 2))
                for m in self.listar_metas()]

    def status_meta_da_categoria(self, categoria, data):
        """Status da meta da categoria no mês de 'data' (None se não houver meta)."""
        meta = self._meta_da_categoria(categoria)
        if meta is None:
            return None
        d = converter_data(data)
        for status in self.status_metas(d.year, d.month):
            if status.categoria == meta.categoria:
                return status
        return None

    # ---------- RF13: exportação de relatórios ----------
    @staticmethod
    def _gravar_csv(caminho, cabecalho, linhas):
        """Grava CSV compatível com Excel pt-BR (separador ';', UTF-8 com BOM)."""
        try:
            with open(caminho, "w", newline="", encoding="utf-8-sig") as arq:
                escritor = csv.writer(arq, delimiter=";")
                escritor.writerow(cabecalho)
                escritor.writerows(linhas)
        except OSError as erro:
            raise ArquivoError(f"Não foi possível gravar '{caminho}': {erro}")

    @staticmethod
    def _virgula(valor):
        """Formata número com 2 casas e vírgula decimal (padrão do Excel em português)."""
        return f"{valor:.2f}".replace(".", ",")

    def exportar_csv(self, caminho, inicio=None, fim=None):
        """Exporta o relatório de movimentações (lista de transações do período)."""
        transacoes = self.listar(inicio=inicio, fim=fim)
        self._gravar_csv(
            caminho, ["id", "tipo", "data", "valor", "categoria", "descricao"],
            [[t.id, t.tipo(), t.data_br, self._virgula(t.valor), t.categoria, t.descricao]
             for t in transacoes])
        return len(transacoes)

    def exportar_relatorio_categoria(self, caminho, tipo="despesa", inicio=None, fim=None):
        """Exporta o relatório por categoria (RF10) para CSV."""
        resumo = self.relatorio_por_categoria(tipo, inicio, fim)
        self._gravar_csv(
            caminho, ["categoria", "total", "percentual"],
            [[r.categoria, self._virgula(r.total), self._virgula(r.percentual)] for r in resumo])
        return len(resumo)

    def exportar_resumo_mensal(self, caminho, ano):
        """Exporta o resumo mensal de um ano para CSV."""
        resumo = self.relatorio_mensal(ano)
        self._gravar_csv(
            caminho, ["mes", "receitas", "despesas", "saldo"],
            [[r.mes, self._virgula(r.receitas), self._virgula(r.despesas), self._virgula(r.saldo)]
             for r in resumo])
        return len(resumo)

    def importar_csv_legado(self, caminho):
        """Importa o CSV do sistema anterior para a conta do usuário."""
        return self._repo.importar_csv(caminho, self._uid)

    # ---------- RF14: backup (operação global sobre o arquivo do banco) ----------
    def fazer_backup(self, destino):
        """Copia o banco para um arquivo de backup (RF14)."""
        self._repo.banco.backup(destino)

    def restaurar_backup(self, origem):
        """Restaura o banco a partir de um backup (RF14); substitui todos os dados."""
        self._repo.banco.restaurar(origem)

    def popular_dados_exemplo(self):
        """Carrega dados de demonstração apenas se este usuário não tiver transações."""
        if self._repo.total_registros(self._uid) > 0:
            return False
        self.registrar_receita("10/05/2026", 3500.00, "Salário", "Pagamento do mês")
        self.registrar_despesa("12/05/2026", 1200.00, "Moradia", "Aluguel do apartamento")
        self.registrar_receita("15/05/2026", 250.50, "Freelance", "Desenvolvimento de site")
        self.registrar_despesa("18/05/2026", 85.90, "Alimentação", "Compras no supermercado")
        self.registrar_despesa("20/05/2026", 45.00, "Transporte", "Combustível")
        self.registrar_receita("25/05/2026", 120.00, "Vendas", "Venda de desapegos")
        self.definir_meta("Alimentação", 100.00)
        self.definir_meta("Transporte", 40.00)
        return True
