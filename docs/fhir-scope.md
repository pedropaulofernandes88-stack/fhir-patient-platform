# Escopo FHIR R4

## Implementado

- JSON FHIR versão `4.0.1`;
- Bundles `transaction` e `collection` administrativa;
- recursos `Patient`, `Encounter`, `Condition`, `Observation`,
  `MedicationRequest`, `Procedure` e `Immunization`;
- leitura por tipo e ID;
- busca por paciente, código, `_count` e `_offset`;
- respostas `Bundle` dos tipos `transaction-response`, `history` e `searchset`;
- `read`, `vread`, histórico por instância e ETag;
- resolução de referências por `fullUrl`, inclusive `urn:uuid`;
- controle otimista opcional por `request.ifMatch` em atualizações;
- erros de validação no formato `OperationOutcome`;
- metadados básicos em `CapabilityStatement`.

## Validações do MVP

- o documento de entrada deve ser um `Bundle` reconhecido;
- cada entrada deve ter recurso, tipo suportado e ID válido;
- identidades e `fullUrl` não podem se repetir no mesmo Bundle;
- entradas de `transaction` devem conter `request.method` e `request.url` coerentes;
- todo recurso clínico deve referenciar um `Patient` existente ou presente no Bundle;
- datas e códigos principais são normalizados para os índices de consulta.

## Deliberadamente fora do escopo

- validação integral dos esquemas e invariantes oficiais;
- validação de perfis nacionais, `StructureDefinition` e `ImplementationGuide`;
- resolução de referências condicionais;
- terminologia remota e validação de `ValueSet`/`CodeSystem`;
- operações `$`, `patch`, `delete` e busca encadeada;
- semântica completa de transações condicionais, `batch` e ETags HTTP condicionais;
- conformidade ou certificação de servidor FHIR.

As escolhas seguem como referência a especificação oficial de
[Bundle](https://hl7.org/fhir/R4/bundle.html) e da
[API REST FHIR R4](https://hl7.org/fhir/R4/http.html).
