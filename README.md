# FHIR Patient Platform

[![qualidade](https://github.com/pedropaulofernandes88-stack/fhir-patient-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/pedropaulofernandes88-stack/fhir-patient-platform/actions/workflows/ci.yml)

MVP de interoperabilidade em saúde que recebe registros clínicos **sintéticos** no
padrão FHIR R4, preserva o JSON original, cria uma projeção pesquisável e apresenta
uma linha do tempo longitudinal do paciente.

> Projeto educacional e de portfólio. Não é um prontuário eletrônico certificado e
> não deve ser usado para assistência clínica ou com dados pessoais reais.

## O problema que este projeto resolve

Dados clínicos costumam estar distribuídos entre sistemas que usam estruturas e
vocabulários diferentes. A plataforma demonstra, em escala de MVP, como um contrato
interoperável pode ser recebido, validado, persistido, consultado e auditado sem
acoplar a aplicação ao formato interno de um fornecedor.

O projeto implementa uma superfície inspirada no
[FHIR R4 REST](https://hl7.org/fhir/R4/http.html) e processa
[Bundles FHIR R4](https://hl7.org/fhir/R4/bundle.html). Os registros de demonstração
são fictícios; em uma evolução, Bundles equivalentes também podem ser gerados pelo
[Synthea](https://github.com/synthetichealth/synthea).

## O que ele demonstra no currículo

- modelagem e interoperabilidade de dados clínicos com FHIR R4;
- API REST com FastAPI e documentação OpenAPI automática;
- transações atômicas, referências `urn:uuid`, versionamento e integridade referencial;
- histórico imutável, `vread`, ETag e controle otimista com `If-Match`;
- persistência com SQLAlchemy e separação entre JSON canônico e índices de busca;
- rastreabilidade por eventos de auditoria sem identificadores de pacientes;
- testes de contrato, análise estática e CI com GitHub Actions;
- comunicação responsável: dados sintéticos, limites e ameaças documentados.

## Arquitetura

```text
Bundle FHIR sintético
        │
        ▼
 FastAPI / validação ─────► OperationOutcome em caso de erro
        │
        ▼
 serviço transacional ───► evento de auditoria agregado
        │
        ▼
 SQLAlchemy + SQLite
 JSON FHIR + índices de busca
        │
        ├────────► API FHIR: read e search
        └────────► API de apoio: pacientes e timeline
                              │
                              ▼
                         Streamlit
```

Decisões e limitações estão detalhadas em
[`docs/architecture.md`](docs/architecture.md) e o subconjunto FHIR em
[`docs/fhir-scope.md`](docs/fhir-scope.md).

## Recursos suportados

`Patient`, `Encounter`, `Condition`, `Observation`, `MedicationRequest`,
`Procedure` e `Immunization`.

| Método | Endpoint | Finalidade |
| --- | --- | --- |
| `GET` | `/fhir/metadata` | CapabilityStatement do servidor |
| `POST` | `/fhir` | Importar Bundle `transaction` atômico |
| `POST` | `/api/import` | Importar Bundle de administração |
| `GET` | `/fhir/{tipo}/{id}` | Ler um recurso e sua versão |
| `GET` | `/fhir/{tipo}/{id}/_history` | Consultar o histórico imutável |
| `GET` | `/fhir/{tipo}/{id}/_history/{versão}` | Ler uma versão específica |
| `GET` | `/fhir/{tipo}?patient=&code=` | Buscar recursos indexados |
| `GET` | `/api/patients` | Listar pacientes para a interface |
| `GET` | `/api/patients/{id}/timeline` | Consultar a linha do tempo |
| `GET` | `/api/audit` | Consultar auditoria agregada |

## Executar localmente

Requisitos: Python 3.11 ou superior.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Em um terminal, inicie a API:

```bash
fhir-platform-api
```

A documentação interativa estará em `http://127.0.0.1:8000/docs`.
Em outro terminal, carregue os registros fictícios:

```bash
python scripts/load_sample.py
```

Depois, inicie o painel:

```bash
streamlit run dashboard.py
```

O banco padrão é `data/fhir.db`. Para outro banco, configure `FHIR_DATABASE_URL`.
PostgreSQL é compatível com a camada SQLAlchemy e requer a instalação do extra
`.[postgres]`; o ambiente validado deste MVP usa SQLite.

## Qualidade

```bash
ruff check .
pytest -q
```

Os testes cobrem saúde e metadados, atomicidade, histórico, controle de concorrência,
resolução de UUIDs, busca, timeline, auditoria e rejeição de referência inválida. O workflow usa ações
compatíveis com o runtime Node.js 24 dos runners atuais.

## Segurança e privacidade

O repositório não contém dados reais. Para um ambiente produtivo seriam obrigatórios,
entre outros controles, autenticação e autorização, TLS, segregação por instituição,
criptografia, consentimento, retenção, trilhas de acesso e revisão de conformidade.
Veja [`docs/security-and-privacy.md`](docs/security-and-privacy.md).

## RNDS e conformidade

A aplicação é um **sandbox FHIR R4**, útil para exercitar conceitos necessários a uma
integração com a RNDS. Ela não declara conformidade com perfis nacionais. O guia da
RNDS adiciona perfis, extensões, terminologias, credenciamento e requisitos de
segurança que não são validados por este MVP. A matriz de aderência e o caminho de
evolução estão em [`docs/rnds-conformance.md`](docs/rnds-conformance.md).

## Próximas evoluções

- OAuth 2.0/SMART on FHIR e autorização por escopo;
- validação oficial contra perfis e terminologias da RNDS;
- PostgreSQL e migrações de esquema;
- importação de uma população sintética gerada pelo Synthea;
- métricas operacionais, paginação por links e testes de carga.

## Licença

MIT. Consulte [`LICENSE`](LICENSE).
