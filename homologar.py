"""Gera HOMOLOGACAO.md: matriz de rastreabilidade requisito -> testes -> resultado.

Uso:  python homologar.py
Cada teste de tests/test_requisitos.py leva o ID do requisito no nome (test_rf07_..., test_rnf05_...).
Ajuste o dicionário REQUISITOS abaixo para que IDs e descrições fiquem idênticos aos da Entrega 1.
"""
import re
import sys
import unittest
from datetime import datetime

REQUISITOS = {
    "RF01": "Cadastrar usuário",
    "RF02": "Autenticar usuário (login) e isolar os dados de cada usuário",
    "RF03": "Cadastrar receitas",
    "RF04": "Cadastrar despesas",
    "RF05": "Listar movimentações",
    "RF06": "Editar movimentações",
    "RF07": "Excluir movimentações",
    "RF08": "Calcular saldo",
    "RF09": "Relatório por categoria",
    "RF10": "Resumo mensal",
    "RF11": "Filtrar por período",
    "RF12": "Metas de gastos por categoria com alertas",
    "RF13": "Exportar dados para CSV",
    "RF14": "Backup e restauração dos dados",
    "RNF03": "Persistência em SQLite",
    "RNF05": "Tratamento de exceções e validações",
}


class Coletor(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.resultados = {}          # nome do teste -> 'OK' | 'FALHA'

    def addSuccess(self, test):
        super().addSuccess(test)
        self.resultados[test.id().split(".")[-1]] = "OK"

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.resultados[test.id().split(".")[-1]] = "FALHA"

    def addError(self, test, err):
        super().addError(test, err)
        self.resultados[test.id().split(".")[-1]] = "FALHA"


def main():
    suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
    resultado = unittest.TextTestRunner(resultclass=Coletor, verbosity=0, stream=open("/dev/null", "w")
                                        if sys.platform != "win32" else sys.stderr).run(suite)
    por_req = {r: [] for r in REQUISITOS}
    for nome, status in sorted(resultado.resultados.items()):
        m = re.match(r"test_(r(?:nf|f)\d+)_", nome)
        if m:
            por_req.setdefault(m.group(1).upper(), []).append((nome, status))

    linhas = ["# Homologação — Controle Financeiro Pessoal 2.0", "",
              f"Gerado em {datetime.now():%d/%m/%Y %H:%M} por `python homologar.py`.", "",
              "| Requisito | Descrição | Testes que o comprovam | Resultado |", "|---|---|---|---|"]
    todos_ok = True
    for req, descricao in REQUISITOS.items():
        testes = por_req.get(req, [])
        ok = bool(testes) and all(s == "OK" for _, s in testes)
        todos_ok &= ok
        nomes = "<br>".join(f"`{n}`" for n, _ in testes) or "—"
        linhas.append(f"| {req} | {descricao} | {nomes} | {'✅ Atendido' if ok else '❌ Pendente'} |")
    total = resultado.testsRun
    linhas += ["", f"**Suíte completa:** {total} testes executados, "
                   f"{len(resultado.failures) + len(resultado.errors)} falha(s).",
               f"**Conclusão:** {'todos os requisitos foram atendidos.' if todos_ok else 'há requisitos pendentes.'}", ""]
    with open("HOMOLOGACAO.md", "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    print(f"{total} testes, {len(resultado.failures) + len(resultado.errors)} falha(s). "
          f"Matriz gravada em HOMOLOGACAO.md")
    return 0 if todos_ok and resultado.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
