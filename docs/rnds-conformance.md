# Matriz de aderência à RNDS

## Conclusão

Este projeto demonstra uma base técnica para interoperabilidade, mas **não é um
servidor homologado ou conforme à RNDS**. A RNDS usa FHIR R4 e publica um Guia de
Implementação que restringe recursos por perfis, extensões e terminologias próprias.

Referências oficiais:

- [Guia de Implementação da RNDS](https://rnds-fhir.saude.gov.br/)
- [Artefatos e perfis publicados](https://rnds-fhir.saude.gov.br/artifacts.html)
- [Downloads do pacote `rnds#1.0.0`](https://rnds-fhir.saude.gov.br/downloads.html)

## Matriz

| Capacidade | Implementação atual | Lacuna para RNDS |
|---|---|---|
| Base FHIR | JSON FHIR R4 `4.0.1` | validar todos os invariantes do padrão |
| Recursos | subconjunto clínico explícito | mapear cada caso de uso aos perfis RNDS corretos |
| Transação | Bundle atômico com POST/PUT | operações e regras específicas do serviço de destino |
| Referências | locais e `urn:uuid` no Bundle | referências condicionais e políticas do ecossistema |
| Versionamento | histórico, `vread`, ETag e `If-Match` | retenção, exclusão lógica e migrações operacionais |
| Perfis | `meta.profile` base nos exemplos | validar `StructureDefinition` do pacote RNDS |
| Terminologias | código e sistema preservados | validar bindings e ValueSets oficiais |
| Segurança | apenas dados sintéticos e auditoria agregada | credenciamento, autenticação, autorização, TLS e gestão de chaves |
| Proveniência | evento técnico agregado | recursos e atributos exigidos por cada fluxo RNDS |
| Operação | SQLite local | PostgreSQL, observabilidade, disponibilidade e recuperação |

## Caminho de validação recomendado

1. Selecionar um caso de uso RNDS específico, por exemplo resultado de exame.
2. Fixar a versão publicada do pacote do guia e registrar seu checksum.
3. Criar exemplos sintéticos que declarem os perfis nacionais aplicáveis.
4. Executar o validador oficial FHIR com o pacote RNDS e tratar erros e alertas.
5. Adicionar testes negativos para cardinalidade, terminologia e referências.
6. Implementar o modelo de segurança e o processo de credenciamento descritos pelo
   Ministério da Saúde em ambiente de homologação.

Sem essas etapas, o termo correto para o repositório é **sandbox FHIR R4 orientado à
preparação para RNDS**, e não “integração RNDS”.
