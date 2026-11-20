"""Gera HOMOLOGACAO.md: matriz de rastreabilidade requisito -> testes -> resultado.

Uso:  python homologar.py
Cada teste de tests/test_requisitos.py leva o ID do requisito no nome (test_rf07_..., test_rnf05_...).
Os IDs e descrições de REQUISITOS são os da proposta (Entrega 1).
"""
import re
import sys
import unittest
from datetime import datetime

REQUISITOS = {
    "RF01": "Permitir cadastro de usuários",
    "RF02": "Permitir autenticação de usuários",
    "RF03": "Cadastrar receitas",
    "RF04": "Cadastrar despesas",
    "RF05": "Listar movimentações financeiras",
    "RF06": "Editar movimentações",
    "RF07": "Excluir movimentações",
    "RF08": "Calcular saldo financeiro",
    "RF09": "Emitir relatório por período",
    "RF10": "Emitir relatório por categoria",
    "RF11": "Cadastrar metas financeiras",
    "RF12": "Acompanhar metas financeiras",
    "RF13": "Exportar relatórios",
    "RF14": "Realizar backup dos dados",
    "RNF01": "Desenvolvimento em Python",
    "RNF02": "Utilização de Programação Orientada a Objetos",
    "RNF03": "Persistência em banco SQLite",
    "RNF04": "Interface simples e intuitiva",
    "RNF05": "Tratamento de exceções",
    "RNF06": "Código documentado",
    "RNF07": "Versionamento em Git",
    "RNF08": "Tempo de resposta inferior a 3 segundos",
}

# Evidências que não podem ser verificadas por teste automatizado.
EVIDENCIAS_MANUAIS = {
    "RNF07": "Repositório Git: https://github.com/diogotrade857-alt/controle-financeiro-pessoal",
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
        nomes = "<br>".join(f"`{n}`" for n, _ in testes)
        if not testes and req in EVIDENCIAS_MANUAIS:
            ok, nomes = True, "Evidência manual: " + EVIDENCIAS_MANUAIS[req]
        todos_ok &= ok
        linhas.append(f"| {req} | {descricao} | {nomes or '—'} | {'✅ Atendido' if ok else '❌ Pendente'} |")
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
