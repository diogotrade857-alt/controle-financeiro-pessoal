# Sistema de Controle Financeiro Pessoal 2.0 — Entrega Final

Aplicação de linha de comando para controle de receitas e despesas pessoais, com **múltiplos usuários**,
**relatórios**, **metas de gastos**, **exportação**, **backup** e persistência em **SQLite**.
Evolução do sistema desenvolvido na disciplina de Programação Orientada a Objetos.

**Autor:** Diogo Alves Guimarães

## Problema, público e escopo

- **Problema:** controlar gastos em planilhas ou cadernos é trabalhoso, propenso a erro e não avisa quando o orçamento estoura.
- **Público-alvo:** pessoas que querem acompanhar suas finanças pessoais de forma simples, sem instalar nada além do Python.
- **Escopo:** registro e consulta de movimentações, saldo, relatórios, metas por categoria, exportação e backup, por usuário.
- **Fora do escopo:** interface gráfica/web, múltiplas moedas, integração bancária, recuperação de senha por e-mail.

## Requisitos atendidos

| ID | Requisito | Onde está |
|---|---|---|
| RF01 | Cadastrar usuário | `usuarios.py` (`ServicoUsuarios.cadastrar`) |
| RF02 | Login e isolamento de dados por usuário | `usuarios.py`, `seguranca.py`, filtro `usuario_id` no repositório |
| RF03–RF04 | Cadastrar receitas e despesas | `servico.py` |
| RF05–RF07 | Listar, editar e excluir por ID | `servico.py`, `repositorio.py` |
| RF08 | Calcular saldo | `ControleFinanceiro.calcular_saldo` |
| RF09 | Relatório por categoria | `relatorio_por_categoria` |
| RF10 | Resumo mensal | `relatorio_mensal` |
| RF11 | Filtro por período | parâmetros `inicio`/`fim` em listagem, saldo, relatórios e exportação |
| RF12 | Metas de gastos com alertas (aviso a 80%, alerta ao exceder) | `definir_meta`, `status_metas` |
| RF13 | Exportar CSV (compatível com Excel pt-BR) | `exportar_csv` |
| RF14 | Backup e restauração | `banco.py` (`Banco.backup` / `Banco.restaurar`) |
| RNF03 | Persistência em SQLite | `banco.py`, `repositorio.py` |
| RNF05 | Tratamento de exceções e validações | `excecoes.py`, setters de `modelos.py` |

A comprovação de cada requisito por testes está em [`HOMOLOGACAO.md`](HOMOLOGACAO.md).

## Como executar

Requer apenas **Python 3.9+** (somente biblioteca padrão; nenhuma dependência externa).

```bash
python main.py                 # usa/cria financeiro.db na pasta atual
python main.py --demo          # cria a conta demo@exemplo.com (senha: demo123) com dados de exemplo
python main.py --db outro.db   # usa outro arquivo de banco
```

Fluxo básico: **Criar conta → Entrar → usar o menu**. Datas no formato `dd/mm/aaaa`; valores aceitam vírgula ou ponto.

### Menu principal

| Opção | Ação |
|---|---|
| 1 / 2 | Adicionar receita / despesa (despesas disparam aviso se a meta da categoria estiver em risco) |
| 3 | Ver transações (com filtro opcional de período) |
| 4 | Ver saldo |
| 5 / 6 | Editar / remover por ID |
| 7 | Relatórios: despesas ou receitas por categoria; resumo mensal do ano |
| 8 | Metas: definir/alterar, acompanhar o mês, remover |
| 9 | Exportar para CSV (opcionalmente por período) |
| 10 / 11 | Backup / restaurar backup (a restauração exige digitar `RESTAURAR`) |
| 12 | Importar o CSV do sistema anterior (`transacoes_poo.csv`) |

## Testes e homologação

```bash
python -m unittest -v     # 52 testes
python homologar.py       # roda tudo e gera HOMOLOGACAO.md (requisito -> testes -> resultado)
```

- `tests/test_mvp.py` — testes da Entrega 2 (regressão).
- `tests/test_requisitos.py` — um ou mais testes por requisito, incluindo fluxo completo pela interface de texto.

## Estrutura

```
main.py                     Interface de linha de comando (menus, leitura de entrada, mensagens)
homologar.py                Gera HOMOLOGACAO.md a partir dos testes
financeiro/
    modelos.py              Domínio: Transacao (abstrata), Receita, Despesa, Meta, fábrica
    usuarios.py             Usuario, RepositorioUsuarios, ServicoUsuarios (RF01/RF02)
    servico.py              Regras de negócio: ControleFinanceiro e objetos de resultado
    repositorio.py          Persistência: RepositorioTransacoes, RepositorioMetas
    banco.py                Conexão SQLite, esquema, migração, backup/restauração
    seguranca.py            Hash de senha (PBKDF2-HMAC-SHA256 com sal)
    excecoes.py             Hierarquia de exceções do domínio
tests/                      Testes automatizados (unittest)
docs/ARQUITETURA.md         Diagramas de classes e de camadas (Mermaid)
docs/ROTEIRO_APRESENTACAO.md  Roteiro da defesa técnica
```

## Decisões de arquitetura

- **Camadas** (interface → serviço → repositório → banco): SQL isolado no repositório, regras no serviço, entrada/saída na interface. Permite testar com banco em memória e trocar a interface sem tocar nas regras.
- **POO:** `Transacao` é abstrata (abstração); `Receita` e `Despesa` a estendem (herança) e implementam `tipo()`/`exibir()` (polimorfismo); atributos validados por `@property` (encapsulamento); `criar_transacao` é uma fábrica.
- **Composição e escopo por usuário:** `ControleFinanceiro` *tem um* repositório e um `usuario_id`; todas as consultas filtram `usuario_id IS ?`, então um usuário não enxerga nem altera dados de outro (testado).
- **Agregações no banco:** saldo e relatórios usam `SUM ... GROUP BY` no SQLite, sem carregar todas as linhas na memória.
- **Segurança de senha:** PBKDF2-HMAC-SHA256, 120 mil iterações, sal aleatório por usuário, comparação em tempo constante; mensagem de erro igual para e-mail inexistente e senha errada.
- **Consultas parametrizadas** em toda a SQL (testado contra injeção).
- **Migração automática:** bancos da Entrega 2 ganham a coluna `usuario_id`; os dados antigos passam a pertencer ao primeiro usuário cadastrado.
- **Exceções próprias** sob `ErroFinanceiro`: a interface captura apenas erros esperados e nunca é derrubada por entrada inválida; bugs reais continuam visíveis.

## Regras de validação

- Valor numérico, finito e estritamente positivo (movimentações e limite de meta).
- Data `dd/mm/aaaa` existente no calendário; data inicial não pode ser posterior à final.
- Categoria obrigatória; categorias são comparadas ignorando maiúsculas/minúsculas em relatórios e metas.
- Nome obrigatório, e-mail em formato válido e único (ignorando caixa), senha com mínimo de 6 caracteres.
- Edição atômica: se qualquer campo for inválido, nada é gravado.
- Backup nunca sobrescreve arquivo existente; restauração valida integridade e estrutura do arquivo antes de substituir os dados.

## Limitações conhecidas

- Valores monetários usam `float` com arredondamento a 2 casas (suficiente para o escopo; `Decimal` seria o próximo passo).
- Restaurar um backup substitui os dados de **todos** os usuários do arquivo.
- Não há bloqueio por tentativas de login nem recuperação de senha.
