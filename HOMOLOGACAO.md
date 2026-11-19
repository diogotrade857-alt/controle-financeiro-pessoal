# Homologação — Controle Financeiro Pessoal 2.0

Gerado em 03/11/2026 22:03 por `python homologar.py`.

| Requisito | Descrição | Testes que o comprovam | Resultado |
|---|---|---|---|
| RF01 | Cadastrar usuário | `test_rf01_cadastrar_usuario`<br>`test_rf01_email_duplicado_ignora_caixa`<br>`test_rf01_rejeita_dados_invalidos` | ✅ Atendido |
| RF02 | Autenticar usuário (login) e isolar os dados de cada usuário | `test_rf02_dados_isolados_entre_usuarios`<br>`test_rf02_login_correto`<br>`test_rf02_login_incorreto`<br>`test_rf02_senha_nao_fica_em_texto_puro` | ✅ Atendido |
| RF03 | Cadastrar receitas | `test_rf03_cadastrar_receita` | ✅ Atendido |
| RF04 | Cadastrar despesas | `test_rf04_cadastrar_despesa` | ✅ Atendido |
| RF05 | Listar movimentações | `test_rf05_listar_movimentacoes` | ✅ Atendido |
| RF06 | Editar movimentações | `test_rf06_editar_movimentacao` | ✅ Atendido |
| RF07 | Excluir movimentações | `test_rf07_excluir_movimentacao` | ✅ Atendido |
| RF08 | Calcular saldo | `test_rf08_calcular_saldo` | ✅ Atendido |
| RF09 | Relatório por categoria | `test_rf09_relatorio_por_categoria` | ✅ Atendido |
| RF10 | Resumo mensal | `test_rf10_resumo_mensal` | ✅ Atendido |
| RF11 | Filtrar por período | `test_rf11_filtrar_por_periodo` | ✅ Atendido |
| RF12 | Metas de gastos por categoria com alertas | `test_rf12_definir_e_atualizar_meta`<br>`test_rf12_meta_invalida`<br>`test_rf12_remover_meta`<br>`test_rf12_status_e_alerta_de_meta` | ✅ Atendido |
| RF13 | Exportar dados para CSV | `test_rf13_exportar_csv`<br>`test_rf13_exportar_para_local_invalido` | ✅ Atendido |
| RF14 | Backup e restauração dos dados | `test_rf14_backup_e_restauracao`<br>`test_rf14_backup_nao_sobrescreve_arquivo`<br>`test_rf14_restaurar_arquivo_invalido` | ✅ Atendido |
| RNF03 | Persistência em SQLite | `test_rnf03_banco_invalido_gera_erro_tratado`<br>`test_rnf03_migra_banco_da_entrega_2`<br>`test_rnf03_persistencia_sqlite_em_arquivo` | ✅ Atendido |
| RNF05 | Tratamento de exceções e validações | `test_rnf05_entradas_invalidas_sao_rejeitadas`<br>`test_rnf05_erros_de_dominio_herdam_de_erro_financeiro`<br>`test_rnf05_importar_csv_inexistente_ou_binario`<br>`test_rnf05_importar_csv_legado_por_usuario`<br>`test_rnf05_sql_injection_nao_funciona` | ✅ Atendido |

**Suíte completa:** 52 testes executados, 0 falha(s).
**Conclusão:** todos os requisitos foram atendidos.
