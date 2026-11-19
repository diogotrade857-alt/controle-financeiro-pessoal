import os
import tempfile
import unittest

from financeiro.excecoes import TransacaoNaoEncontradaError, ValidacaoError
from financeiro.modelos import Despesa, Receita, Transacao, criar_transacao
from financeiro.repositorio import RepositorioTransacoes
from financeiro.servico import ControleFinanceiro


class TestModelos(unittest.TestCase):
    def test_classe_abstrata_nao_instancia(self):
        with self.assertRaises(TypeError):
            Transacao("10/05/2026", 10, "X", "")

    def test_polimorfismo_tipo_e_exibir(self):
        r = Receita("10/05/2026", 100, "Salário", "mês", id=1)
        d = Despesa("11/05/2026", 50, "Moradia", "aluguel", id=2)
        self.assertEqual((r.tipo(), d.tipo()), ("receita", "despesa"))
        self.assertIn("RECEITA", r.exibir())
        self.assertIn("DESPESA", d.exibir())

    def test_valor_deve_ser_positivo(self):
        for invalido in (0, -5, "abc", None, float("nan"), float("inf")):
            with self.assertRaises(ValidacaoError):
                Receita("10/05/2026", invalido, "X", "")

    def test_data_invalida(self):
        for invalida in ("31/02/2026", "2026-05-10", "abc", ""):
            with self.assertRaises(ValidacaoError):
                Despesa(invalida, 10, "X", "")

    def test_categoria_obrigatoria(self):
        with self.assertRaises(ValidacaoError):
            Despesa("10/05/2026", 10, "   ", "")

    def test_fabrica_tipo_desconhecido(self):
        with self.assertRaises(ValidacaoError):
            criar_transacao("outro", "10/05/2026", 10, "X")


class TestServico(unittest.TestCase):
    def setUp(self):
        self.repo = RepositorioTransacoes(":memory:")
        self.sistema = ControleFinanceiro(self.repo)

    def tearDown(self):
        self.repo.fechar()

    def test_cadastrar_e_listar(self):
        r = self.sistema.registrar_receita("10/05/2026", 3500, "Salário", "mês")
        d = self.sistema.registrar_despesa("12/05/2026", 1200, "Moradia", "aluguel")
        self.assertEqual((r.id, d.id), (1, 2))
        lista = self.sistema.listar()
        self.assertEqual([type(t) for t in lista], [Receita, Despesa])
        self.assertEqual(len(self.sistema.listar("despesa")), 1)

    def test_saldo(self):
        self.sistema.registrar_receita("10/05/2026", 3500, "Salário")
        self.sistema.registrar_despesa("12/05/2026", 1200, "Moradia")
        self.sistema.registrar_despesa("18/05/2026", 85.90, "Alimentação")
        s = self.sistema.calcular_saldo()
        self.assertEqual((s.receitas, s.despesas, s.total), (3500.0, 1285.9, 2214.1))

    def test_saldo_vazio(self):
        self.assertEqual(self.sistema.calcular_saldo().total, 0)

    def test_editar_parcialmente(self):
        t = self.sistema.registrar_despesa("12/05/2026", 100, "Moradia", "aluguel")
        self.sistema.editar(t.id, valor="150,00".replace(",", "."), descricao="novo")
        novo = self.sistema.obter(t.id)
        self.assertEqual((novo.valor, novo.descricao, novo.categoria), (150.0, "novo", "Moradia"))

    def test_editar_invalido_nao_persiste(self):
        t = self.sistema.registrar_despesa("12/05/2026", 100, "Moradia", "aluguel")
        with self.assertRaises(ValidacaoError):
            self.sistema.editar(t.id, categoria="Outra", valor=-1)
        self.assertEqual(self.sistema.obter(t.id).categoria, "Moradia")

    def test_remover(self):
        t = self.sistema.registrar_receita("10/05/2026", 10, "X")
        self.sistema.remover(t.id)
        self.assertEqual(self.sistema.listar(), [])
        with self.assertRaises(TransacaoNaoEncontradaError):
            self.sistema.remover(t.id)

    def test_id_inexistente(self):
        with self.assertRaises(TransacaoNaoEncontradaError):
            self.sistema.obter(999)
        with self.assertRaises(TransacaoNaoEncontradaError):
            self.sistema.editar(999, valor=10)

    def test_ponto_e_virgula_na_descricao_nao_quebra(self):
        t = self.sistema.registrar_despesa("12/05/2026", 10, "X", "a;b;c")
        self.assertEqual(self.sistema.obter(t.id).descricao, "a;b;c")

    def test_dados_exemplo_so_em_banco_vazio(self):
        self.assertTrue(self.sistema.popular_dados_exemplo())
        self.assertFalse(self.sistema.popular_dados_exemplo())
        self.assertEqual(len(self.sistema.listar()), 6)


class TestPersistencia(unittest.TestCase):
    def test_dados_sobrevivem_ao_reabrir_arquivo(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "teste.db")
            repo = RepositorioTransacoes(caminho)
            ControleFinanceiro(repo).registrar_receita("10/05/2026", 99.9, "Salário", "x")
            repo.fechar()
            repo2 = RepositorioTransacoes(caminho)
            lista = ControleFinanceiro(repo2).listar()
            repo2.fechar()
            self.assertEqual(len(lista), 1)
            self.assertEqual(lista[0].valor, 99.9)

    def test_importar_csv_antigo_sem_duplicar(self):
        with tempfile.TemporaryDirectory() as pasta:
            csv = os.path.join(pasta, "transacoes_poo.csv")
            with open(csv, "w", encoding="utf-8") as f:
                f.write("1;receita;10/05/2026;3500.0;Salário;Pagamento do mês\n")
                f.write("2;despesa;12/05/2026;1200.0;Moradia;Aluguel\n")
                f.write("linha quebrada\n")
                f.write("3;despesa;32/13/2026;10.0;X;data inválida\n")
            repo = RepositorioTransacoes(":memory:")
            self.assertEqual(repo.importar_csv(csv), 2)
            self.assertEqual(repo.importar_csv(csv), 0)   # idempotente
            self.assertEqual(repo.total_registros(), 2)
            repo.fechar()


if __name__ == "__main__":
    unittest.main()
