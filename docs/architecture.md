# Arquitetura e metodologia

## Objetivo do MVP

Demonstrar um fluxo completo e auditável para dados clínicos sintéticos: entrada em
FHIR R4, validação mínima, persistência, busca, composição de uma visão longitudinal e
visualização. A prioridade é tornar decisões e limites observáveis, não reproduzir um
servidor FHIR de produção.

## Método de desenvolvimento

1. **Definir o contrato:** FHIR R4 JSON e um subconjunto explícito de recursos.
2. **Preservar a fonte:** armazenar o recurso recebido sem remodelá-lo de forma
   destrutiva.
3. **Projetar para consulta:** extrair somente campos necessários para integridade,
   busca e ordenação da timeline.
4. **Falhar antes de gravar:** validar todo o Bundle e suas referências antes da
   transação de persistência.
5. **Tornar mudanças observáveis:** atualizar `meta.versionId`, `meta.lastUpdated`,
   preservar snapshots imutáveis e registrar uma auditoria agregada.
6. **Verificar por comportamento:** testar contratos HTTP, idempotência, integridade e
   consultas, além de análise estática no CI.

## Componentes

- `fhir.py`: validação e extração de campos do padrão recebido;
- `service.py`: casos de uso transacionais e consultas;
- `models.py`: recursos FHIR e eventos de auditoria;
- `main.py`: contrato HTTP e respostas FHIR;
- `dashboard.py`: exploração de pacientes e eventos;
- `data/sample`: cenário clínico inteiramente fictício e reproduzível.

## Estratégia de persistência

Cada recurso mantém o JSON FHIR completo em `payload`. Uma projeção relacional guarda
tipo, ID, referência do paciente, código e instante clínico. Isso preserva flexibilidade
sem obrigar buscas frequentes em JSON, mas não substitui índices especializados ou um
repositório FHIR completo.

A chave `(resource_type, resource_id)` identifica o estado atual. Cada criação ou
atualização também produz um snapshot em `fhir_resource_versions`, permitindo
`history` e `vread`. ETags fracos representam `versionId`, e `request.ifMatch` rejeita
uma atualização baseada em versão obsoleta. Migrações de esquema e retenção ainda são
necessárias antes de produção.

## Critérios de conclusão

- importar o Bundle sintético sem gravações parciais;
- rejeitar referência a paciente inexistente com `OperationOutcome`;
- repetir a importação sem duplicar recursos;
- resolver referências `urn:uuid` e rejeitar URLs de requisição inconsistentes;
- recuperar versões anteriores e detectar conflito por `If-Match`;
- ler e pesquisar recursos FHIR;
- ordenar os eventos na timeline de um paciente;
- registrar auditoria sem identificadores clínicos;
- executar testes e análise estática automaticamente.
