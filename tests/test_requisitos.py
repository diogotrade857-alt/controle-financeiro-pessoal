"""Testes de homologação: cada método test_rfXX_* / test_rnfXX_* comprova um requisito.

O script homologar.py usa o ID no nome do teste para montar a matriz de rastreabilidade.
"""
import ast
import csv
import os
import time
import sqlite3
import tempfile
import unittest
from unittest import mock

import main as cli
from financeiro import seguranca
from financeiro.banco import Banco
from financeiro.excecoes import (AutenticacaoError, BackupError, ErroFinanceiro,
                                 MetaNaoEncontradaError, TransacaoNaoEncontradaError,
                                 ValidacaoError)
from financeiro.repositorio import RepositorioTransacoes
from financeiro.servico import ControleFinanceiro
from financeiro.usuarios import RepositorioUsuarios, ServicoUsuarios


class Base(unittest.TestCase):
    def setUp(self):
        # Menos iterações de PBKDF2 só nos testes, para a suíte rodar rápido.
        patcher = mock.patch.object(seguranca, "ITERACOES", 1000)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.repo = RepositorioTransacoes(Banco(":memory:"))
        self.usuarios = ServicoUsuarios(RepositorioUsuarios(self.repo.banco))
        self.ana = self.usuarios.cadastrar("Ana", "ana@exemplo.com", "senha123")
        self.bia = self.usuarios.cadastrar("Bia", "bia@exemplo.com", "senha456")
        self.sa = ControleFinanceiro(self.repo, self.ana.id)
        self.sb = ControleFinanceiro(self.repo, self.bia.id)
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.repo.fechar()
        self.tmp.cleanup()

    def caminho(self, nome):
        return os.path.join(self.tmp.name, nome)


class TestUsuarios(Base):
    def test_rf01_cadastrar_usuario(self):
        self.assertEqual((self.ana.nome, self.ana.email), ("Ana", "ana@exemplo.com"))
        self.assertEqual(self.usuarios.total_usuarios(), 2)

    def test_rf01_rejeita_dados_invalidos(self):
        casos = [("", "x@y.com", "senha123"), ("Cris", "sem-arroba", "senha123"),
                 ("Cris", "c@y.com", "123"), ("Cris", "c@y.com", None)]
        for nome, email, senha in casos:
            with self.assertRaises(ValidacaoError):
                self.usuarios.cadastrar(nome, email, senha)

    def test_rf01_email_duplicado_ignora_caixa(self):
        with self.assertRaises(ValidacaoError):
            self.usuarios.cadastrar("Outra Ana", "ANA@Exemplo.com", "senha123")

    def test_rf02_login_correto(self):
        self.assertEqual(self.usuarios.autenticar("ANA@exemplo.com", "senha123").id, self.ana.id)

    def test_rf02_login_incorreto(self):
        with self.assertRaises(AutenticacaoError):
            self.usuarios.autenticar("ana@exemplo.com", "errada")
        with self.assertRaises(AutenticacaoError):
            self.usuarios.autenticar("naoexiste@exemplo.com", "senha123")

    def test_rf02_senha_nao_fica_em_texto_puro(self):
        linhas = self.repo.banco.conn.execute("SELECT senha_hash FROM usuarios").fetchall()
        for l in linhas:
            self.assertNotIn("senha", l[0])
            self.assertTrue(l[0].startswith("pbkdf2_sha256$"))
        h1, h2 = seguranca.gerar_hash("abc123"), seguranca.gerar_hash("abc123")
        self.assertNotEqual(h1, h2)                 # sal aleatório
        self.assertTrue(seguranca.verificar("abc123", h1))
        self.assertFalse(seguranca.verificar("abc124", h1))
        self.assertFalse(seguranca.verificar("x", "lixo"))

    def test_rf02_dados_isolados_entre_usuarios(self):
        t = self.sa.registrar_despesa("10/05/2026", 50, "Mercado")
        self.sb.registrar_despesa("11/05/2026", 70, "Lazer")
        self.assertEqual([x.categoria for x in self.sa.listar()], ["Mercado"])
        self.assertEqual([x.categoria for x in self.sb.listar()], ["Lazer"])
        with self.assertRaises(TransacaoNaoEncontradaError):
            self.sb.obter(t.id)
        with self.assertRaises(TransacaoNaoEncontradaError):
            self.sb.editar(t.id, valor=1)
        with self.assertRaises(TransacaoNaoEncontradaError):
            self.sb.remover(t.id)
        self.assertEqual(self.sa.calcular_saldo().despesas, 50.0)


class TestTransacoes(Base):
    def test_rf03_cadastrar_receita(self):
        t = self.sa.registrar_receita("10/05/2026", 100, "Salário")
        self.assertEqual((t.tipo(), t.valor), ("receita", 100.0))

    def test_rf04_cadastrar_despesa(self):
        t = self.sa.registrar_despesa("10/05/2026", "25.5", "Mercado")
        self.assertEqual((t.tipo(), t.valor), ("despesa", 25.5))

    def test_rf05_listar_movimentacoes(self):
        self.sa.registrar_receita("10/05/2026", 100, "A")
        self.sa.registrar_despesa("09/05/2026", 10, "B")
        self.assertEqual([t.categoria for t in self.sa.listar()], ["B", "A"])   # ordenado por data
        self.assertEqual(len(self.sa.listar("receita")), 1)
        with self.assertRaises(ValidacaoError):
            self.sa.listar("outro")

    def test_rf06_editar_movimentacao(self):
        t = self.sa.registrar_despesa("10/05/2026", 100, "A", "x")
        self.sa.editar(t.id, valor=200, descricao="y")
        novo = self.sa.obter(t.id)
        self.assertEqual((novo.valor, novo.descricao, novo.categoria), (200.0, "y", "A"))
        with self.assertRaises(ValidacaoError):
            self.sa.editar(t.id, categoria="Z", valor=-1)
        self.assertEqual(self.sa.obter(t.id).categoria, "A")     # atômico

    def test_rf07_excluir_movimentacao(self):
        t = self.sa.registrar_receita("10/05/2026", 10, "A")
        self.sa.remover(t.id)
        self.assertEqual(self.sa.listar(), [])
        with self.assertRaises(TransacaoNaoEncontradaError):
            self.sa.remover(t.id)

    def test_rf08_calcular_saldo(self):
        self.sa.registrar_receita("10/05/2026", 3500, "Salário")
        self.sa.registrar_despesa("12/05/2026", 1200, "Moradia")
        self.sa.registrar_despesa("18/05/2026", 85.90, "Mercado")
        s = self.sa.calcular_saldo()
        self.assertEqual((s.receitas, s.despesas, s.total), (3500.0, 1285.9, 2214.1))
        self.assertEqual(self.sb.calcular_saldo().total, 0)


class TestRelatorios(Base):
    def setUp(self):
        super().setUp()
        s = self.sa
        s.registrar_receita("05/04/2026", 1000, "Salário")
        s.registrar_despesa("10/05/2026", 300, "Mercado")
        s.registrar_despesa("11/05/2026", 100, "mercado")      # caixa diferente: mesma categoria
        s.registrar_despesa("12/05/2026", 100, "Lazer")
        s.registrar_receita("15/05/2026", 2000, "Salário")

    def test_rf10_relatorio_por_categoria(self):
        r = self.sa.relatorio_por_categoria("despesa")
        self.assertEqual([(x.categoria, x.total, x.percentual) for x in r],
                         [("Mercado", 400.0, 80.0), ("Lazer", 100.0, 20.0)])
        self.assertEqual(self.sa.relatorio_por_categoria("receita")[0].total, 3000.0)
        self.assertEqual(self.sb.relatorio_por_categoria("despesa"), [])
        with self.assertRaises(ValidacaoError):
            self.sa.relatorio_por_categoria("x")

    def test_rf09_relatorio_por_periodo(self):
        r = self.sa.relatorio_por_periodo("01/05/2026", "31/05/2026")
        self.assertEqual((r.receitas, r.despesas, r.saldo, r.qtd_receitas, r.qtd_despesas),
                         (2000.0, 500.0, 1500.0, 1, 3))
        tudo = self.sa.relatorio_por_periodo()
        self.assertEqual((tudo.receitas, tudo.qtd_receitas), (3000.0, 2))
        vazio = self.sb.relatorio_por_periodo("01/05/2026", "31/05/2026")
        self.assertEqual((vazio.receitas, vazio.despesas, vazio.saldo), (0.0, 0.0, 0.0))
        with self.assertRaises(ValidacaoError):
            self.sa.relatorio_por_periodo("31/05/2026", "01/05/2026")

    def test_rf09_resumo_mensal(self):
        r = self.sa.relatorio_mensal(2026)
        self.assertEqual([(x.mes, x.receitas, x.despesas, x.saldo) for x in r],
                         [("2026-04", 1000.0, 0.0, 1000.0), ("2026-05", 2000.0, 500.0, 1500.0)])
        self.assertEqual(self.sa.relatorio_mensal(2025), [])
        for invalido in ("abc", 1800, None):
            with self.assertRaises(ValidacaoError):
                self.sa.relatorio_mensal(invalido)

    def test_rf09_filtrar_por_periodo(self):
        self.assertEqual(len(self.sa.listar(inicio="01/05/2026", fim="11/05/2026")), 2)
        self.assertEqual(self.sa.calcular_saldo(inicio="01/05/2026", fim="31/05/2026").total, 1500.0)
        self.assertEqual(len(self.sa.listar(inicio="12/05/2026")), 2)
        with self.assertRaises(ValidacaoError):
            self.sa.listar(inicio="31/05/2026", fim="01/05/2026")
        with self.assertRaises(ValidacaoError):
            self.sa.listar(inicio="32/05/2026")


class TestMetas(Base):
    def test_rf11_definir_e_atualizar_meta(self):
        self.sa.definir_meta("Mercado", 500)
        self.sa.definir_meta("mercado", 600)                  # atualiza, não duplica
        self.assertEqual([(m.categoria, m.limite) for m in self.sa.listar_metas()], [("Mercado", 600.0)])
        self.assertEqual(self.sb.listar_metas(), [])

    def test_rf11_meta_invalida(self):
        for categoria, limite in [("", 10), ("X", 0), ("X", -5), ("X", "abc")]:
            with self.assertRaises(ValidacaoError):
                self.sa.definir_meta(categoria, limite)

    def test_rf12_status_e_alerta_de_meta(self):
        self.sa.definir_meta("Mercado", 100)
        self.sa.registrar_despesa("10/05/2026", 85, "Mercado")
        self.sa.registrar_despesa("10/06/2026", 999, "Mercado")      # outro mês: não conta
        st = self.sa.status_metas(2026, 5)[0]
        self.assertEqual((st.gasto, st.percentual, st.restante, st.excedida), (85.0, 85.0, 15.0, False))
        self.sa.registrar_despesa("20/05/2026", 30, "mercado")
        self.assertTrue(self.sa.status_meta_da_categoria("Mercado", "20/05/2026").excedida)
        self.assertIsNone(self.sa.status_meta_da_categoria("Sem meta", "20/05/2026"))
        with self.assertRaises(ValidacaoError):
            self.sa.status_metas(2026, 13)

    def test_rf11_remover_meta(self):
        self.sa.definir_meta("Mercado", 100)
        self.sa.remover_meta("MERCADO")
        self.assertEqual(self.sa.listar_metas(), [])
        with self.assertRaises(MetaNaoEncontradaError):
            self.sa.remover_meta("Mercado")


class TestArquivos(Base):
    def test_rf13_exportar_csv(self):
        self.sa.registrar_despesa("10/05/2026", 12.5, "Mercado", "pão; leite; \"ovos\"")
        self.sa.registrar_receita("11/06/2026", 100, "Extra")
        self.sb.registrar_receita("11/05/2026", 999, "Outro usuário")
        destino = self.caminho("saida.csv")
        self.assertEqual(self.sa.exportar_csv(destino, inicio="01/05/2026", fim="31/05/2026"), 1)
        with open(destino, encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.reader(f, delimiter=";"))
        self.assertEqual(linhas[0], ["id", "tipo", "data", "valor", "categoria", "descricao"])
        self.assertEqual(linhas[1][1:], ["despesa", "10/05/2026", "12,50", "Mercado", "pão; leite; \"ovos\""])
        self.assertEqual(len(linhas), 2)

    def test_rf13_exportar_relatorio_por_categoria(self):
        self.sa.registrar_despesa("10/05/2026", 300, "Mercado")
        self.sa.registrar_despesa("11/05/2026", 100, "Lazer")
        self.sa.registrar_receita("12/05/2026", 999, "Salário")
        destino = self.caminho("categorias.csv")
        self.assertEqual(self.sa.exportar_relatorio_categoria(destino, "despesa"), 2)
        with open(destino, encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.reader(f, delimiter=";"))
        self.assertEqual(linhas, [["categoria", "total", "percentual"],
                                  ["Mercado", "300,00", "75,00"], ["Lazer", "100,00", "25,00"]])
        with self.assertRaises(ValidacaoError):
            self.sa.exportar_relatorio_categoria(destino, "outro")

    def test_rf13_exportar_resumo_mensal(self):
        self.sa.registrar_receita("05/04/2026", 1000, "Salário")
        self.sa.registrar_despesa("10/05/2026", 250.5, "Mercado")
        destino = self.caminho("mensal.csv")
        self.assertEqual(self.sa.exportar_resumo_mensal(destino, 2026), 2)
        with open(destino, encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.reader(f, delimiter=";"))
        self.assertEqual(linhas[0], ["mes", "receitas", "despesas", "saldo"])
        self.assertEqual(linhas[1], ["2026-04", "1000,00", "0,00", "1000,00"])
        self.assertEqual(linhas[2], ["2026-05", "0,00", "250,50", "-250,50"])
        with self.assertRaises(ErroFinanceiro):
            self.sa.exportar_resumo_mensal(self.caminho("sem_pasta/x.csv"), 2026)

    def test_rf13_exportar_para_local_invalido(self):
        with self.assertRaises(ErroFinanceiro):
            self.sa.exportar_csv(self.caminho("pasta_inexistente/x.csv"))

    def test_rf14_backup_e_restauracao(self):
        self.sa.registrar_receita("10/05/2026", 100, "A")
        bkp = self.caminho("bkp.db")
        self.sa.fazer_backup(bkp)
        self.sa.registrar_receita("11/05/2026", 50, "B")
        self.sa.remover(self.sa.listar()[0].id)
        self.sa.restaurar_backup(bkp)
        self.assertEqual([t.categoria for t in self.sa.listar()], ["A"])
        self.assertEqual(self.usuarios.autenticar("ana@exemplo.com", "senha123").id, self.ana.id)

    def test_rf14_backup_nao_sobrescreve_arquivo(self):
        bkp = self.caminho("bkp.db")
        self.sa.fazer_backup(bkp)
        with self.assertRaises(BackupError):
            self.sa.fazer_backup(bkp)

    def test_rf14_restaurar_arquivo_invalido(self):
        with self.assertRaises(BackupError):
            self.sa.restaurar_backup(self.caminho("nao_existe.db"))
        lixo = self.caminho("lixo.db")
        with open(lixo, "w") as f:
            f.write("isto não é um banco sqlite " * 50)
        with self.assertRaises(BackupError):
            self.sa.restaurar_backup(lixo)
        outro = self.caminho("outro.db")
        c = sqlite3.connect(outro); c.execute("CREATE TABLE x (a)"); c.commit(); c.close()
        with self.assertRaises(BackupError):
            self.sa.restaurar_backup(outro)
        self.assertEqual(self.usuarios.total_usuarios(), 2)          # banco atual intacto


class TestRequisitosNaoFuncionais(Base):
    RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _arquivos_codigo(self):
        pasta = os.path.join(self.RAIZ, "financeiro")
        achados = [os.path.join(pasta, n) for n in sorted(os.listdir(pasta)) if n.endswith(".py")]
        return achados + [os.path.join(self.RAIZ, "main.py")]

    def test_rnf01_python_somente_biblioteca_padrao(self):
        permitidos = {"abc", "argparse", "calendar", "csv", "dataclasses", "datetime", "getpass",
                      "hashlib", "hmac", "math", "os", "re", "sqlite3", "financeiro"}
        for caminho in self._arquivos_codigo():
            with open(caminho, encoding="utf-8") as f:
                arvore = ast.parse(f.read())
            for no in ast.walk(arvore):
                if isinstance(no, ast.Import):
                    modulos = {a.name.split(".")[0] for a in no.names}
                elif isinstance(no, ast.ImportFrom) and no.level == 0:
                    modulos = {no.module.split(".")[0]}
                else:
                    continue
                self.assertTrue(modulos <= permitidos, f"{caminho}: {modulos - permitidos}")

    def test_rnf02_orientacao_a_objetos(self):
        from abc import ABC
        from financeiro.modelos import Despesa, Receita, Transacao
        self.assertTrue(issubclass(Transacao, ABC))                       # abstração
        with self.assertRaises(TypeError):
            Transacao("10/05/2026", 10, "X")
        self.assertTrue(issubclass(Receita, Transacao) and issubclass(Despesa, Transacao))   # herança
        r, d = Receita("10/05/2026", 10, "X"), Despesa("10/05/2026", 10, "X")
        self.assertNotEqual((r.tipo(), r.exibir()[:9]), (d.tipo(), d.exibir()[:9]))      # polimorfismo
        with self.assertRaises(ValidacaoError):                                         # encapsulamento
            r.valor = -5
        self.assertIs(self.sa._repo, self.repo)                                         # composição

    def test_rnf04_interface_simples_e_mensagens_claras(self):
        saida = []
        entradas = ["1", "ana@exemplo.com", "99", "2", "10/05/2026", "150,50", "Mercado", "", "0", "0"]
        with mock.patch("builtins.input", side_effect=entradas), \
             mock.patch.object(cli, "ler_senha", return_value="senha123"), \
             mock.patch("builtins.print", side_effect=lambda *a, **k: saida.append(" ".join(map(str, a)))):
            cli.menu_inicial(self.repo, self.usuarios)
        texto = "\n".join(saida)
        self.assertIn("1 - Adicionar Receita", texto)         # menu numerado
        self.assertIn("Opção inválida", texto)                # opção errada não derruba o programa
        self.assertIn("Registrado com sucesso", texto)        # aceitou vírgula decimal
        self.assertNotIn("Traceback", texto)

    def test_rnf06_codigo_documentado(self):
        sem_doc = []
        for caminho in self._arquivos_codigo():
            with open(caminho, encoding="utf-8") as f:
                arvore = ast.parse(f.read())
            nome = os.path.basename(caminho)
            if not ast.get_docstring(arvore):
                sem_doc.append(f"{nome} (módulo)")
            for no in ast.walk(arvore):
                if isinstance(no, ast.ClassDef) and not ast.get_docstring(no):
                    sem_doc.append(f"{nome}: classe {no.name}")
                funcoes = [no] if isinstance(no, ast.FunctionDef) else []
                if isinstance(no, ast.ClassDef):
                    funcoes = [m for m in no.body if isinstance(m, ast.FunctionDef)]
                for f in funcoes:
                    decoradores = [ast.unparse(d) for d in f.decorator_list]
                    if f.name.startswith("_") or any("property" in d or ".setter" in d for d in decoradores):
                        continue
                    if not ast.get_docstring(f):
                        sem_doc.append(f"{nome}: {f.name}")
        self.assertEqual(sem_doc, [])
        self.assertTrue(os.path.exists(os.path.join(self.RAIZ, "README.md")))

    def test_rnf08_tempo_de_resposta_menor_que_3_segundos(self):
        for i in range(2000):
            dia = 1 + i % 28
            self.sa.registrar_despesa(f"{dia:02d}/{1 + i % 12:02d}/2026", 10 + i % 90, f"Cat{i % 15}")
        destino = self.caminho("tempo.csv")
        operacoes = {
            "listar": lambda: self.sa.listar(),
            "saldo": lambda: self.sa.calcular_saldo(),
            "periodo": lambda: self.sa.relatorio_por_periodo("01/03/2026", "30/06/2026"),
            "categoria": lambda: self.sa.relatorio_por_categoria("despesa"),
            "mensal": lambda: self.sa.relatorio_mensal(2026),
            "exportar": lambda: self.sa.exportar_csv(destino),
        }
        for nome, operacao in operacoes.items():
            inicio = time.perf_counter()
            operacao()
            self.assertLess(time.perf_counter() - inicio, 3.0, nome)


class TestPersistenciaEMigracao(unittest.TestCase):
    def test_rnf03_persistencia_sqlite_em_arquivo(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "p.db")
            repo = RepositorioTransacoes(caminho)
            u = ServicoUsuarios(RepositorioUsuarios(repo.banco)).cadastrar("Ana", "a@x.com", "senha123")
            ControleFinanceiro(repo, u.id).registrar_receita("10/05/2026", 99.9, "A")
            repo.fechar()
            repo2 = RepositorioTransacoes(caminho)
            lista = ControleFinanceiro(repo2, u.id).listar()
            repo2.fechar()
            self.assertEqual((len(lista), lista[0].valor), (1, 99.9))

    def test_rnf03_migra_banco_da_entrega_2(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "antigo.db")
            c = sqlite3.connect(caminho)
            c.execute("CREATE TABLE transacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                      "tipo TEXT NOT NULL, data TEXT NOT NULL, valor REAL NOT NULL, "
                      "categoria TEXT NOT NULL, descricao TEXT NOT NULL DEFAULT '')")
            c.execute("INSERT INTO transacoes (tipo,data,valor,categoria,descricao) "
                      "VALUES ('receita','2026-05-10',100,'Salário','antigo')")
            c.commit(); c.close()
            repo = RepositorioTransacoes(caminho)
            self.assertEqual(len(repo.listar()), 1)                  # dado sem dono preservado
            ana = ServicoUsuarios(RepositorioUsuarios(repo.banco)).cadastrar("Ana", "a@x.com", "senha123")
            self.assertEqual([t.descricao for t in ControleFinanceiro(repo, ana.id).listar()], ["antigo"])
            bia = ServicoUsuarios(RepositorioUsuarios(repo.banco)).cadastrar("Bia", "b@x.com", "senha123")
            self.assertEqual(ControleFinanceiro(repo, bia.id).listar(), [])   # só o 1º usuário herda
            repo.fechar()

    def test_rnf03_banco_invalido_gera_erro_tratado(self):
        with tempfile.TemporaryDirectory() as pasta:
            lixo = os.path.join(pasta, "lixo.db")
            with open(lixo, "w") as f:
                f.write("não sou sqlite " * 100)
            with self.assertRaises(ErroFinanceiro):
                Banco(lixo)


class TestRobustez(Base):
    def test_rnf05_erros_de_dominio_herdam_de_erro_financeiro(self):
        for erro in (ValidacaoError, TransacaoNaoEncontradaError, AutenticacaoError,
                     MetaNaoEncontradaError, BackupError):
            self.assertTrue(issubclass(erro, ErroFinanceiro))

    def test_rnf05_entradas_invalidas_sao_rejeitadas(self):
        for valor in (0, -1, "abc", None, float("nan"), float("inf")):
            with self.assertRaises(ValidacaoError):
                self.sa.registrar_despesa("10/05/2026", valor, "X")
        for data in ("31/02/2026", "2026-05-10", "", None):
            with self.assertRaises(ValidacaoError):
                self.sa.registrar_receita(data, 10, "X")
        with self.assertRaises(ValidacaoError):
            self.sa.registrar_receita("10/05/2026", 10, "   ")

    def test_rnf05_sql_injection_nao_funciona(self):
        self.sa.registrar_despesa("10/05/2026", 10, "x'); DROP TABLE transacoes;--", "'; DELETE FROM usuarios;--")
        self.assertEqual(len(self.sa.listar()), 1)
        self.assertEqual(self.usuarios.total_usuarios(), 2)

    def test_rnf05_importar_csv_inexistente_ou_binario(self):
        with self.assertRaises(ErroFinanceiro):
            self.sa.importar_csv_legado(self.caminho("nao_existe.csv"))
        binario = self.caminho("bin.csv")
        with open(binario, "wb") as f:
            f.write(b"\xff\xfe\x00\x80" * 20)
        with self.assertRaises(ErroFinanceiro):
            self.sa.importar_csv_legado(binario)

    def test_rnf05_importar_csv_legado_por_usuario(self):
        csv_antigo = self.caminho("transacoes_poo.csv")
        with open(csv_antigo, "w", encoding="utf-8") as f:
            f.write("1;receita;10/05/2026;3500.0;Salário;mês\nlinha quebrada\n3;despesa;32/13/2026;1;X;y\n")
        self.assertEqual(self.sa.importar_csv_legado(csv_antigo), 1)
        self.assertEqual(self.sa.importar_csv_legado(csv_antigo), 0)
        self.assertEqual(self.sb.listar(), [])


class TestInterfaceCLI(Base):
    """Fluxo completo pela interface de texto, simulando o teclado."""

    def executar(self, entradas, senhas=()):
        saida = []
        with mock.patch("builtins.input", side_effect=list(entradas)), \
             mock.patch.object(cli, "ler_senha", side_effect=list(senhas)), \
             mock.patch("builtins.print", side_effect=lambda *a, **k: saida.append(" ".join(map(str, a)))):
            cli.menu_inicial(self.repo, self.usuarios)
        return "\n".join(saida)

    def test_fluxo_completo_login_cadastro_relatorio_metas(self):
        texto = self.executar([
            "2", "Caio", "caio@exemplo.com",                      # criar conta
            "1", "caio@exemplo.com",                              # entrar
            "8", "1", "Mercado", "100,00",                        # definir meta
            "2", "10/05/2026", "85,00", "Mercado", "feira",       # despesa -> aviso 85%
            "2", "11/05/2026", "30,00", "Mercado", "mais",        # despesa -> meta excedida
            "1", "10/05/2026", "1000", "Salário", "",             # receita
            "4",                                                  # saldo
            "7", "2", "", "",                                     # relatório por categoria
            "3", "n",                                             # listar
            "2", "10/05/2026", "abc", "X", "",                    # valor inválido: erro, sem derrubar
            "6", "99",                                            # id inexistente: erro, sem derrubar
            "0", "0",                                             # sair da conta, encerrar
        ], senhas=["senha123", "senha123", "senha123"])
        self.assertIn("Conta criada com sucesso", texto)
        self.assertIn("[AVISO] Meta de 'Mercado' em 85.0%", texto)
        self.assertIn("[ALERTA] Meta de 'Mercado' EXCEDIDA", texto)
        self.assertIn("Saldo Final:    R$ 885.00", texto)
        self.assertIn("DESPESAS POR CATEGORIA", texto)
        self.assertIn("Erro: O valor da transação deve ser numérico.", texto)
        self.assertIn("Erro: Transação ID 99 não encontrada.", texto)

    def test_login_invalido_e_senhas_diferentes(self):
        texto = self.executar(["1", "ana@exemplo.com", "2", "X", "x@y.com", "0"],
                              senhas=["errada", "senha123", "outra"])
        self.assertIn("Erro: E-mail ou senha incorretos.", texto)
        self.assertIn("Erro: As senhas não coincidem.", texto)


if __name__ == "__main__":
    unittest.main()
