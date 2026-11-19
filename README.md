# Controle Financeiro Pessoal 2.0

Projeto final da disciplina. É um programa de terminal em Python para registrar receitas e despesas, ver o saldo e acompanhar os gastos. Os dados ficam salvos em um banco SQLite.

Ele é a evolução do sistema que fiz em Programação Orientada a Objetos (que guardava tudo em um arquivo CSV). Nesta versão acrescentei login com vários usuários, relatórios, metas de gastos, exportação e backup.

Autor: Diogo Alves Guimarães

## O problema

Controlar gastos em caderno ou planilha dá trabalho, é fácil errar uma conta e nada avisa quando o dinheiro do mês está acabando. A ideia do programa é deixar isso simples para uma pessoa que quer organizar as próprias finanças e não quer instalar nada além do Python.

O que o sistema faz: cadastro e consulta de movimentações, saldo, relatórios, metas por categoria, exportação e backup, tudo separado por usuário.

O que ficou de fora: interface gráfica ou web, várias moedas, ligação com banco e recuperação de senha por e-mail.

## Requisitos

| ID | O que o sistema faz | Onde está no código |
|---|---|---|
| RF01 | Cadastrar usuário | `usuarios.py` |
| RF02 | Login, com dados separados por usuário | `usuarios.py`, `seguranca.py`, `repositorio.py` |
| RF03 | Cadastrar receitas | `servico.py` |
| RF04 | Cadastrar despesas | `servico.py` |
| RF05 | Listar movimentações | `servico.py` |
| RF06 | Editar movimentações | `servico.py` |
| RF07 | Excluir movimentações | `servico.py` |
| RF08 | Calcular o saldo | `servico.py` |
| RF09 | Relatório por categoria | `servico.py` |
| RF10 | Resumo mensal | `servico.py` |
| RF11 | Filtrar por período | `servico.py` |
| RF12 | Metas de gasto com alerta | `servico.py` |
| RF13 | Exportar para CSV | `servico.py` |
| RF14 | Backup e restauração | `banco.py` |
| RNF03 | Salvar em SQLite | `banco.py`, `repositorio.py` |
| RNF05 | Tratar erros e validar dados | `excecoes.py`, `modelos.py` |

Os testes que comprovam cada requisito estão no arquivo [HOMOLOGACAO.md](HOMOLOGACAO.md).

## Como rodar

Precisa só do Python 3.9 ou mais novo. Não tem nenhuma biblioteca para instalar.

```
python main.py
```

Para testar rápido com dados de exemplo:

```
python main.py --demo
```

Isso cria uma conta de teste (e-mail `demo@exemplo.com`, senha `demo123`) com algumas movimentações. Também dá para escolher o arquivo do banco com `python main.py --db nome.db`.

Na primeira vez, crie uma conta e depois entre com ela. As datas vão no formato `dd/mm/aaaa` e os valores podem ter vírgula ou ponto.

### Menu

| Opção | O que faz |
|---|---|
| 1 e 2 | Adiciona receita ou despesa. Se a despesa chegar perto do limite da meta, o programa avisa |
| 3 | Lista as transações, com filtro de período opcional |
| 4 | Mostra o saldo |
| 5 e 6 | Edita ou remove uma transação pelo ID |
| 7 | Relatórios: por categoria ou resumo mensal |
| 8 | Metas: definir, acompanhar o mês e remover |
| 9 | Exporta as transações para CSV |
| 10 e 11 | Faz backup do banco ou restaura um backup (precisa digitar `RESTAURAR` para confirmar) |
| 12 | Importa o CSV do sistema antigo (`transacoes_poo.csv`) |
| 0 | Sai da conta |

## Testes

```
python -m unittest -v
python homologar.py
```

O primeiro comando roda os 52 testes. O segundo roda os testes e gera o `HOMOLOGACAO.md`, que mostra cada requisito com os testes dele.

Os testes estão em `tests/`. O `test_mvp.py` é da Entrega 2 e o `test_requisitos.py` foi feito para esta entrega.

## Organização dos arquivos

```
main.py             menus e entrada de dados (terminal)
homologar.py        gera o HOMOLOGACAO.md
financeiro/
    modelos.py      classes Transacao, Receita, Despesa e Meta
    usuarios.py     cadastro e login
    servico.py      regras de negócio (saldo, relatórios, metas...)
    repositorio.py  comandos SQL
    banco.py        conexão com o SQLite, backup e restauração
    seguranca.py    criptografia da senha
    excecoes.py     erros do sistema
tests/              testes automatizados
docs/               diagramas e roteiro da apresentação
```

## Como o código foi organizado

Dividi o programa em camadas: a interface (`main.py`) só conversa com o usuário, o serviço (`servico.py`) tem as regras e o repositório (`repositorio.py`) é o único que escreve SQL. Assim, dá para testar as regras usando um banco na memória, sem depender do terminal. Os diagramas estão em [docs/ARQUITETURA.md](docs/ARQUITETURA.md).

Na parte de orientação a objetos, `Transacao` é uma classe abstrata e `Receita` e `Despesa` herdam dela. Cada uma mostra a transação do seu jeito (polimorfismo). Os atributos são validados com `@property`, e uma função `criar_transacao` escolhe qual classe criar.

Cada usuário só enxerga as próprias transações, porque todas as consultas filtram pelo `usuario_id`. Existe um teste que tenta acessar dados de outro usuário para garantir isso.

As senhas não ficam salvas como texto: uso PBKDF2 (da biblioteca padrão do Python) com um sal diferente para cada usuário. O SQL usa sempre parâmetros, o que evita injeção de SQL.

Os erros esperados (valor inválido, data errada, login incorreto etc.) têm classes próprias que herdam de `ErroFinanceiro`. A interface captura só essas, então uma entrada errada não derruba o programa, mas um bug de verdade continua aparecendo.

Se alguém abrir um banco da Entrega 2, o programa adiciona sozinho a coluna que faltava. As transações antigas passam a ser do primeiro usuário que for criado.

## Validações

- O valor tem que ser um número maior que zero.
- A data precisa existir no calendário. Em filtros, a data inicial não pode vir depois da final.
- A categoria é obrigatória. Nos relatórios e nas metas, "Mercado" e "mercado" contam como a mesma.
- O nome é obrigatório, o e-mail precisa ser válido e não pode repetir, e a senha precisa ter pelo menos 6 caracteres.
- Na edição, se algum campo for inválido, nada é alterado.
- O backup não sobrescreve um arquivo que já existe. Antes de restaurar, o programa confere se o arquivo é um banco válido deste sistema.

## Limitações

- O dinheiro é guardado como `float`, arredondado em 2 casas. Funciona para este projeto, mas o mais correto seria usar `Decimal`.
- Restaurar um backup troca os dados de todos os usuários do banco, não só os de quem está logado.
- Não há bloqueio depois de várias senhas erradas nem recuperação de senha.
