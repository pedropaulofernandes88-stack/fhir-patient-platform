# Escopo FHIR R4

## Implementado

- JSON FHIR versão `4.0.1`;
- Bundles `transaction`, `batch` e `collection`;
- recursos `Patient`, `Encounter`, `Condition`, `Observation`,
  `MedicationRequest`, `Procedure` e `Immunization`;
- leitura por tipo e ID;
- busca por paciente, código, `_count` e `_offset`;
- respostas `Bundle` dos tipos `transaction-response`, `batch-response` e
  `searchset`;
- erros de validação no formato `OperationOutcome`;
- metadados básicos em `CapabilityStatement`.

## Validações do MVP

- o documento de entrada deve ser um `Bundle` reconhecido;
- cada entrada deve ter recurso, tipo suportado e ID válido;
- identidades e `fullUrl` não podem se repetir no mesmo Bundle;
- entradas de transaction/batch devem conter `request`;
- todo recurso clínico deve referenciar um `Patient` existente ou presente no Bundle;
- datas e códigos principais são normalizados para os índices de consulta.

## Deliberadamente fora do escopo

- validação integral dos esquemas e invariantes oficiais;
- perfis nacionais, `StructureDefinition` e `ImplementationGuide`;
- resolução de referências condicionais ou UUIDs entre entradas;
- terminologia remota e validação de `ValueSet`/`CodeSystem`;
- operações `$`, `history`, `vread`, `patch` e busca encadeada;
- semântica completa de transaction condicional e controle de concorrência;
- conformidade ou certificação de servidor FHIR.

As escolhas seguem como referência a especificação oficial de
[Bundle](https://hl7.org/fhir/R4/bundle.html) e da
[API REST FHIR R4](https://hl7.org/fhir/R4/http.html).
