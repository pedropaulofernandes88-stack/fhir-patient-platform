# Contribuindo

1. Descreva o comportamento FHIR e a referência normativa na issue.
2. Inclua testes de contrato positivos e negativos.
3. Não amplie a declaração de conformidade além do que os testes comprovam.
4. Execute `ruff check .` e `pytest -q`.
5. Use apenas pacientes e identificadores sintéticos.

Mudanças de persistência devem incluir uma estratégia explícita de migração antes de produção.
