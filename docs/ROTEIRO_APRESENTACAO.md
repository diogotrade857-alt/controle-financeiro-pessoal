# Roteiro da defesa técnica (≈10 min)

1. **Problema e público (1 min):** controle financeiro pessoal; quem usa; o que ficou fora do escopo.
2. **Evolução do projeto (1 min):** Entrega 1 (planejamento) → Entrega 2 (CRUD + SQLite) → Entrega 3 (usuários, relatórios, metas, exportação, backup). Mostrar `HOMOLOGACAO.md`.
3. **Demonstração ao vivo (3 min):** `python main.py --demo` → login → adicionar despesa que dispara alerta de meta → relatório por categoria → exportar CSV e abrir no Excel → backup → restaurar.
4. **Decisões de arquitetura (3 min)** — cada uma com o "porquê":
   - Camadas e composição → testar com banco em memória; SQL isolado.
   - Classe abstrata + polimorfismo → o serviço não depende de `Receita`/`Despesa` concretas.
   - Escopo por `usuario_id` em toda consulta → isolamento entre usuários testado.
   - Agregações em SQL → não carregar tudo na memória.
   - Hierarquia `ErroFinanceiro` → a interface nunca cai por entrada inválida, mas bugs reais aparecem.
   - PBKDF2 com sal → senha nunca em texto puro.
5. **Desafios superados (1,5 min):**
   - Migrar o banco da Entrega 2 sem perder dados (coluna `usuario_id`, dados antigos herdados pelo 1º usuário).
   - Backup seguro: não sobrescrever, validar integridade e estrutura antes de restaurar.
   - Categorias com caixa diferente ("Mercado"/"mercado") somadas juntas em relatórios e metas.
   - Exportar CSV compatível com Excel pt-BR (`;`, vírgula decimal, BOM UTF-8).
6. **Limitações e próximos passos (0,5 min):** `Decimal` para dinheiro, interface web/GUI, bloqueio por tentativas de login.

**Perguntas prováveis:** por que `float` e não `Decimal`? · como evita que um usuário veja dados de outro? · o que acontece se o backup estiver corrompido? · por que SQLite?
