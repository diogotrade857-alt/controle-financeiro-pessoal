# Homologação — Controle Financeiro Pessoal 2.0

Gerado em 20/11/2026 03:19 por `python homologar.py`.

| Requisito | Descrição | Testes que o comprovam | Resultado |
|---|---|---|---|
| RF01 | Permitir cadastro de usuários | `test_rf01_cadastrar_usuario`<br>`test_rf01_email_duplicado_ignora_caixa`<br>`test_rf01_rejeita_dados_invalidos` | ✅ Atendido |
| RF02 | Permitir autenticação de usuários | `test_rf02_dados_isolados_entre_usuarios`<br>`test_rf02_login_correto`<br>`test_rf02_login_incorreto`<br>`test_rf02_senha_nao_fica_em_texto_puro` | ✅ Atendido |
| RF03 | Cadastrar receitas | `test_rf03_cadastrar_receita` | ✅ Atendido |
| RF04 | Cadastrar despesas | `test_rf04_cadastrar_despesa` | ✅ Atendido |
| RF05 | Listar movimentações financeiras | `test_rf05_listar_movimentacoes` | ✅ Atendido |
| RF06 | Editar movimentações | `test_rf06_editar_movimentacao` | ✅ Atendido |
| RF07 | Excluir movimentações | `test_rf07_excluir_movimentacao` | ✅ Atendido |
| RF08 | Calcular saldo financeiro | `test_rf08_calcular_saldo` | ✅ Atendido |
| RF09 | Emitir relatório por período | `test_rf09_filtrar_por_periodo`<br>`test_rf09_relatorio_por_periodo`<br>`test_rf09_resumo_mensal` | ✅ Atendido |
| RF10 | Emitir relatório por categoria | `test_rf10_relatorio_por_categoria` | ✅ Atendido |
| RF11 | Cadastrar metas financeiras | `test_rf11_definir_e_atualizar_meta`<br>`test_rf11_meta_invalida`<br>`test_rf11_remover_meta` | ✅ Atendido |
| RF12 | Acompanhar metas financeiras | `test_rf12_status_e_alerta_de_meta` | ✅ Atendido |
| RF13 | Exportar relatórios | `test_rf13_exportar_csv`<br>`test_rf13_exportar_para_local_invalido`<br>`test_rf13_exportar_relatorio_por_categoria`<br>`test_rf13_exportar_resumo_mensal` | ✅ Atendido |
| RF14 | Realizar backup dos dados | `test_rf14_backup_e_restauracao`<br>`test_rf14_backup_nao_sobrescreve_arquivo`<br>`test_rf14_restaurar_arquivo_invalido` | ✅ Atendido |
| RNF01 | Desenvolvimento em Python | `test_rnf01_python_somente_biblioteca_padrao` | ✅ Atendido |
| RNF02 | Utilização de Programação Orientada a Objetos | `test_rnf02_orientacao_a_objetos` | ✅ Atendido |
| RNF03 | Persistência em banco SQLite | `test_rnf03_banco_invalido_gera_erro_tratado`<br>`test_rnf03_migra_banco_da_entrega_2`<br>`test_rnf03_persistencia_sqlite_em_arquivo` | ✅ Atendido |
| RNF04 | Interface simples e intuitiva | `test_rnf04_interface_simples_e_mensagens_claras` | ✅ Atendido |
| RNF05 | Tratamento de exceções | `test_rnf05_entradas_invalidas_sao_rejeitadas`<br>`test_rnf05_erros_de_dominio_herdam_de_erro_financeiro`<br>`test_rnf05_importar_csv_inexistente_ou_binario`<br>`test_rnf05_importar_csv_legado_por_usuario`<br>`test_rnf05_sql_injection_nao_funciona` | ✅ Atendido |
| RNF06 | Código documentado | `test_rnf06_codigo_documentado` | ✅ Atendido |
| RNF07 | Versionamento em Git | Evidência manual: Repositório Git: https://github.com/diogotrade857-alt/controle-financeiro-pessoal | ✅ Atendido |
| RNF08 | Tempo de resposta inferior a 3 segundos | `test_rnf08_tempo_de_resposta_menor_que_3_segundos` | ✅ Atendido |

**Suíte completa:** 60 testes executados, 0 falha(s).
**Conclusão:** todos os requisitos foram atendidos.
