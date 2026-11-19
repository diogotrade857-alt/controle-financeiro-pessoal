"""Interface de linha de comando do Sistema de Controle Financeiro Pessoal 2.0.

Uso:
    python main.py                 # usa/cria financeiro.db na pasta atual
    python main.py --demo          # cria o usuário demo@exemplo.com (senha demo123) com dados de exemplo
    python main.py --db outro.db   # escolhe o arquivo do banco
"""
import argparse
import getpass
import os
import sqlite3
from datetime import datetime

from financeiro.banco import Banco
from financeiro.excecoes import ErroFinanceiro, ValidacaoError
from financeiro.repositorio import RepositorioTransacoes
from financeiro.servico import ControleFinanceiro
from financeiro.usuarios import RepositorioUsuarios, ServicoUsuarios

LIMIAR_AVISO_META = 80.0   # % do limite a partir do qual o usuário é avisado


def moeda(v):
    return f"R$ {v:.2f}"


# ------------------------------- entrada -------------------------------
def ler_senha(mensagem):
    return getpass.getpass(mensagem)


def ler_inteiro(mensagem):
    try:
        return int(input(mensagem).strip())
    except ValueError:
        raise ValidacaoError("Digite um número inteiro.")


def ler_valor(mensagem):
    # Aceita vírgula decimal (padrão brasileiro) e ponto.
    return input(mensagem).strip().replace(",", ".")


def ler_periodo():
    inicio = input("Data inicial (dd/mm/aaaa, ENTER = sem limite): ").strip() or None
    fim = input("Data final   (dd/mm/aaaa, ENTER = sem limite): ").strip() or None
    return inicio, fim


def ler_mes_ano():
    texto = input("Mês (mm/aaaa, ENTER = mês atual): ").strip()
    if not texto:
        hoje = datetime.now()
        return hoje.year, hoje.month
    try:
        mes, ano = texto.split("/")
        return int(ano), int(mes)
    except ValueError:
        raise ValidacaoError("Use o formato mm/aaaa (ex: 05/2026).")


# ------------------------------- transações -------------------------------
def avisar_meta(sistema, t):
    status = sistema.status_meta_da_categoria(t.categoria, t.data)
    if status is None:
        return
    if status.excedida:
        print(f"[ALERTA] Meta de '{status.categoria}' EXCEDIDA: gasto {moeda(status.gasto)} "
              f"de {moeda(status.limite)} ({status.percentual}%).")
    elif status.percentual >= LIMIAR_AVISO_META:
        print(f"[AVISO] Meta de '{status.categoria}' em {status.percentual}% "
              f"(restam {moeda(status.restante)}).")


def cadastrar(sistema, receita):
    data = input("Data (dd/mm/aaaa): ")
    valor = ler_valor("Valor (ex: 150,50): ")
    categoria = input("Categoria: ")
    descricao = input("Descrição: ")
    if receita:
        t = sistema.registrar_receita(data, valor, categoria, descricao)
    else:
        t = sistema.registrar_despesa(data, valor, categoria, descricao)
    print(f"Registrado com sucesso! ID {t.id}.")
    if not receita:
        avisar_meta(sistema, t)


def listar(sistema, inicio=None, fim=None):
    transacoes = sistema.listar(inicio=inicio, fim=fim)
    if not transacoes:
        print("Nenhuma transação encontrada.")
        return False
    print("\n=== LISTA DE TRANSAÇÕES ===")
    for t in transacoes:
        print(t.exibir())     # polimorfismo: Receita e Despesa formatam de modos diferentes
    return True


def listar_com_filtro(sistema):
    if input("Filtrar por período? (s/N): ").strip().lower() == "s":
        inicio, fim = ler_periodo()
        listar(sistema, inicio, fim)
    else:
        listar(sistema)


def mostrar_saldo(sistema):
    s = sistema.calcular_saldo()
    print("\n=== RESUMO FINANCEIRO ===")
    print(f"Total Receitas: {moeda(s.receitas)}")
    print(f"Total Despesas: {moeda(s.despesas)}")
    print(f"Saldo Final:    {moeda(s.total)}")


def editar(sistema):
    if not listar(sistema):
        return
    id_ = ler_inteiro("\nID da transação a editar: ")
    atual = sistema.obter(id_)
    print("Novo valor ou ENTER para manter o atual:")
    data = input(f"Data [{atual.data_br}]: ").strip() or None
    valor = ler_valor(f"Valor [{atual.valor:.2f}]: ") or None
    categoria = input(f"Categoria [{atual.categoria}]: ").strip() or None
    descricao = input(f"Descrição [{atual.descricao}]: ").strip() or None
    sistema.editar(id_, data, valor, categoria, descricao)
    print("Transação atualizada com sucesso!")


def remover(sistema):
    if not listar(sistema):
        return
    id_ = ler_inteiro("\nID da transação a remover: ")
    sistema.remover(id_)
    print(f"Transação ID {id_} removida com sucesso!")


# ------------------------------- relatórios -------------------------------
def relatorio_categoria(sistema, tipo):
    inicio, fim = ler_periodo()
    linhas = sistema.relatorio_por_categoria(tipo, inicio, fim)
    if not linhas:
        print("Nenhum dado no período.")
        return
    print(f"\n=== {tipo.upper()}S POR CATEGORIA ===")
    for r in linhas:
        print(f"{r.categoria:<20} {moeda(r.total):>14}  {r.percentual:>5.1f}%")


def relatorio_mensal(sistema):
    ano = input("Ano (aaaa, ENTER = ano atual): ").strip() or datetime.now().year
    linhas = sistema.relatorio_mensal(ano)
    if not linhas:
        print("Nenhum dado no ano informado.")
        return
    print(f"\n=== RESUMO MENSAL {ano} ===")
    print(f"{'Mês':<9}{'Receitas':>14}{'Despesas':>14}{'Saldo':>14}")
    for r in linhas:
        print(f"{r.mes:<9}{moeda(r.receitas):>14}{moeda(r.despesas):>14}{moeda(r.saldo):>14}")


def menu_relatorios(sistema):
    print("\n1 - Despesas por categoria\n2 - Receitas por categoria\n3 - Resumo mensal do ano")
    op = input("Opção: ").strip()
    if op == "1":
        relatorio_categoria(sistema, "despesa")
    elif op == "2":
        relatorio_categoria(sistema, "receita")
    elif op == "3":
        relatorio_mensal(sistema)
    else:
        print("Opção inválida!")


# ------------------------------- metas -------------------------------
def menu_metas(sistema):
    print("\n1 - Definir/alterar meta\n2 - Acompanhar metas do mês\n3 - Remover meta")
    op = input("Opção: ").strip()
    if op == "1":
        categoria = input("Categoria: ")
        meta = sistema.definir_meta(categoria, ler_valor("Limite mensal (ex: 500,00): "))
        print(f"Meta de '{meta.categoria}' definida em {moeda(meta.limite)}.")
    elif op == "2":
        ano, mes = ler_mes_ano()
        status = sistema.status_metas(ano, mes)
        if not status:
            print("Nenhuma meta cadastrada.")
        for s in status:
            situacao = "EXCEDIDA" if s.excedida else "ok"
            print(f"{s.categoria:<18} gasto {moeda(s.gasto)} / {moeda(s.limite)} "
                  f"({s.percentual}%) [{situacao}]")
    elif op == "3":
        sistema.remover_meta(input("Categoria: "))
        print("Meta removida.")
    else:
        print("Opção inválida!")


# ------------------------------- arquivos -------------------------------
def exportar(sistema):
    caminho = input("Arquivo de destino [exportacao_financeira.csv]: ").strip() \
        or "exportacao_financeira.csv"
    inicio, fim = ler_periodo()
    print(f"{sistema.exportar_csv(caminho, inicio, fim)} transação(ões) exportada(s) para '{caminho}'.")


def backup(sistema):
    padrao = datetime.now().strftime("backup_%Y%m%d_%H%M%S.db")
    destino = input(f"Arquivo de backup [{padrao}]: ").strip() or padrao
    sistema.fazer_backup(destino)
    print(f"Backup criado em '{destino}'.")


def restaurar(sistema):
    """Retorna True se restaurou (o usuário atual precisa entrar de novo)."""
    origem = input("Arquivo de backup a restaurar: ").strip()
    print("ATENÇÃO: isto substitui TODOS os dados atuais (de todos os usuários).")
    if input("Digite RESTAURAR para confirmar: ").strip() != "RESTAURAR":
        print("Operação cancelada.")
        return False
    sistema.restaurar_backup(origem)
    print("Backup restaurado. Faça login novamente.")
    return True


def importar_csv(sistema):
    caminho = input("Caminho do CSV antigo [transacoes_poo.csv]: ").strip() or "transacoes_poo.csv"
    if not os.path.exists(caminho):
        print("Arquivo não encontrado.")
        return
    print(f"{sistema.importar_csv_legado(caminho)} registro(s) importado(s).")


# ------------------------------- menus -------------------------------
def menu_principal(repo, usuario):
    sistema = ControleFinanceiro(repo, usuario.id)
    print(f"\nOlá, {usuario.nome}!")
    while True:
        print("\n1 - Adicionar Receita")
        print("2 - Adicionar Despesa")
        print("3 - Ver Transações")
        print("4 - Ver Saldo Total")
        print("5 - Editar Transação")
        print("6 - Remover Transação")
        print("7 - Relatórios")
        print("8 - Metas de gastos")
        print("9 - Exportar para CSV")
        print("10 - Backup do banco")
        print("11 - Restaurar backup")
        print("12 - Importar CSV do sistema anterior")
        print("0 - Sair da conta")
        opcao = input("Digite a opção desejada: ").strip()
        if opcao == "0":
            return
        try:
            if opcao in ("1", "2"):
                cadastrar(sistema, receita=(opcao == "1"))
            elif opcao == "3":
                listar_com_filtro(sistema)
            elif opcao == "4":
                mostrar_saldo(sistema)
            elif opcao == "5":
                editar(sistema)
            elif opcao == "6":
                remover(sistema)
            elif opcao == "7":
                menu_relatorios(sistema)
            elif opcao == "8":
                menu_metas(sistema)
            elif opcao == "9":
                exportar(sistema)
            elif opcao == "10":
                backup(sistema)
            elif opcao == "11":
                if restaurar(sistema):
                    return
            elif opcao == "12":
                importar_csv(sistema)
            else:
                print("Opção inválida! Tente novamente.")
        except ErroFinanceiro as erro:
            print(f"Erro: {erro}")


def criar_conta(usuarios):
    nome = input("Nome: ")
    email = input("E-mail: ")
    senha = ler_senha("Senha (mín. 6 caracteres): ")
    if senha != ler_senha("Confirme a senha: "):
        raise ValidacaoError("As senhas não coincidem.")
    usuarios.cadastrar(nome, email, senha)
    print("Conta criada com sucesso! Faça login para continuar.")


def menu_inicial(repo, usuarios):
    print("--- Sistema de Controle Financeiro Pessoal 2.0 ---")
    while True:
        print("\n1 - Entrar\n2 - Criar conta\n0 - Encerrar")
        opcao = input("Digite a opção desejada: ").strip()
        if opcao == "0":
            print("Encerrando o sistema. Até logo!")
            return
        try:
            if opcao == "1":
                usuario = usuarios.autenticar(input("E-mail: "), ler_senha("Senha: "))
                menu_principal(repo, usuario)
            elif opcao == "2":
                criar_conta(usuarios)
            else:
                print("Opção inválida! Tente novamente.")
        except ErroFinanceiro as erro:
            print(f"Erro: {erro}")


def preparar_demo(repo, usuarios):
    if usuarios.total_usuarios() > 0:
        return
    demo = usuarios.cadastrar("Usuário Demo", "demo@exemplo.com", "demo123")
    ControleFinanceiro(repo, demo.id).popular_dados_exemplo()
    print("[INFO] Conta de demonstração criada: demo@exemplo.com / demo123")


def main():
    parser = argparse.ArgumentParser(description="Controle Financeiro Pessoal 2.0")
    parser.add_argument("--db", default="financeiro.db", help="arquivo SQLite (padrão: financeiro.db)")
    parser.add_argument("--demo", action="store_true",
                        help="cria conta e dados de exemplo se não houver usuários")
    args = parser.parse_args()

    try:
        repo = RepositorioTransacoes(Banco(args.db))
    except ErroFinanceiro as erro:
        print(f"Erro: {erro}")
        return 1
    usuarios = ServicoUsuarios(RepositorioUsuarios(repo.banco))
    try:
        if args.demo:
            preparar_demo(repo, usuarios)
        menu_inicial(repo, usuarios)
    except (KeyboardInterrupt, EOFError):
        print("\nEntrada encerrada. Até logo!")
    except sqlite3.Error as erro:
        print(f"Erro inesperado no banco de dados: {erro}")
        return 1
    finally:
        repo.fechar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
