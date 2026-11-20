"""Camada de domínio: classes que representam as transações financeiras.

Conceitos de POO aplicados:
    - Abstração:       Transacao é abstrata e define o contrato (tipo, exibir).
    - Encapsulamento:  atributos protegidos (_x) acessados por @property com validação.
    - Herança:         Receita e Despesa estendem Transacao.
    - Polimorfismo:    tipo() e exibir() se comportam de forma diferente em cada filha.
"""
import math
from abc import ABC, abstractmethod
from datetime import date, datetime

from financeiro.excecoes import ValidacaoError

FORMATO_DATA = "%d/%m/%Y"


def converter_data(valor):
    """Converte 'dd/mm/aaaa' (ou um objeto date) em date; lança ValidacaoError se inválida."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor).strip(), FORMATO_DATA).date()
    except ValueError:
        raise ValidacaoError("Data inválida. Use o formato dd/mm/aaaa (ex: 25/05/2026).")


def numero_positivo(valor, sujeito):
    """Converte para float exigindo número finito e > 0; arredonda a 2 casas."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValidacaoError(f"{sujeito} deve ser numérico.")
    if not math.isfinite(numero) or numero <= 0:
        raise ValidacaoError(f"{sujeito} deve ser estritamente positivo.")
    return round(numero, 2)


def categoria_valida(valor):
    """Remove espaços da categoria e rejeita texto vazio."""
    texto = str(valor).strip()
    if not texto:
        raise ValidacaoError("A categoria é obrigatória.")
    return texto


class Transacao(ABC):
    """Classe abstrata: não pode ser instanciada diretamente."""

    def __init__(self, data, valor, categoria, descricao="", id=None):
        self._id = id
        # Atribuições via property para que a validação rode já na criação.
        self.data = data
        self.valor = valor
        self.categoria = categoria
        self.descricao = descricao

    # --- ID: somente leitura. Quem define é o repositório ao gravar no banco. ---
    @property
    def id(self):
        return self._id

    def atribuir_id(self, novo_id):
        """Uso interno da camada de persistência após o INSERT."""
        self._id = novo_id

    # --- Atributos validados ---
    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, nova_data):
        self._data = converter_data(nova_data)

    @property
    def data_br(self):
        return self._data.strftime(FORMATO_DATA)

    @property
    def valor(self):
        return self._valor

    @valor.setter
    def valor(self, novo_valor):
        self._valor = numero_positivo(novo_valor, "O valor da transação")

    @property
    def categoria(self):
        return self._categoria

    @categoria.setter
    def categoria(self, nova_categoria):
        self._categoria = categoria_valida(nova_categoria)

    @property
    def descricao(self):
        return self._descricao

    @descricao.setter
    def descricao(self, nova_descricao):
        self._descricao = str(nova_descricao).strip()

    # --- Contrato que as classes filhas são obrigadas a cumprir ---
    @abstractmethod
    def tipo(self):
        """Retorna 'receita' ou 'despesa'."""

    @abstractmethod
    def exibir(self):
        """Retorna a linha de texto formatada da transação."""

    def _corpo(self):
        return (f"Data: {self.data_br} | Valor: R$ {self.valor:.2f} | "
                f"Categoria: {self.categoria} | Descrição: {self.descricao}")

    def __repr__(self):
        return (f"{type(self).__name__}(id={self.id}, data={self.data_br}, "
                f"valor={self.valor}, categoria={self.categoria!r})")


class Receita(Transacao):
    """Entrada de dinheiro (salário, freelance, vendas etc.)."""
    def tipo(self):
        """Retorna o identificador do tipo: 'receita'."""
        return "receita"

    def exibir(self):
        """Texto de uma linha para mostrar a receita ao usuário."""
        return f"[ID: {self.id}] RECEITA | {self._corpo()}"


class Despesa(Transacao):
    """Saída de dinheiro (aluguel, mercado, transporte etc.)."""
    def tipo(self):
        """Retorna o identificador do tipo: 'despesa'."""
        return "despesa"

    def exibir(self):
        """Texto de uma linha para mostrar a despesa ao usuário."""
        return f"[ID: {self.id}] DESPESA | {self._corpo()}"


_TIPOS = {"receita": Receita, "despesa": Despesa}


def criar_transacao(tipo, data, valor, categoria, descricao="", id=None):
    """Fábrica: devolve a subclasse correta a partir do texto do tipo."""
    try:
        classe = _TIPOS[str(tipo).strip().lower()]
    except KeyError:
        raise ValidacaoError(f"Tipo de transação desconhecido: {tipo!r}.")
    return classe(data, valor, categoria, descricao, id=id)


class Meta:
    """Limite mensal de gastos para uma categoria (RF12)."""

    def __init__(self, categoria, limite, id=None):
        self._id = id
        self.categoria = categoria
        self.limite = limite

    @property
    def id(self):
        return self._id

    @property
    def categoria(self):
        return self._categoria

    @categoria.setter
    def categoria(self, nova):
        self._categoria = categoria_valida(nova)

    @property
    def limite(self):
        return self._limite

    @limite.setter
    def limite(self, novo):
        self._limite = numero_positivo(novo, "O limite da meta")

    def __repr__(self):
        return f"Meta(id={self.id}, categoria={self.categoria!r}, limite={self.limite})"
