# Segurança, privacidade e uso responsável

## Classificação dos dados

Todos os nomes, identificadores e eventos do cenário são fictícios e foram criados
para demonstração. O projeto não precisa e não deve receber prontuários ou dados
pessoais reais.

## Controles presentes no MVP

- banco local ignorado pelo Git;
- validação de IDs, tipos e referências antes da gravação;
- transação de banco por Bundle;
- consultas parametrizadas pelo SQLAlchemy;
- auditoria de volumes e resultado da importação sem ID de paciente;
- resposta estruturada para falhas de validação;
- dependências e testes verificados no CI.

## Modelo simplificado de ameaças

| Risco | Impacto | Controle necessário em produção |
| --- | --- | --- |
| Acesso indevido a prontuários | Exposição de dado sensível | OAuth/SMART, RBAC/ABAC e MFA |
| Vazamento em trânsito ou repouso | Violação de confidencialidade | TLS e criptografia com gestão de chaves |
| Alteração não autorizada | Dano clínico e perda de integridade | Histórico imutável, assinatura e controle de versão |
| Enumeração de pacientes | Reidentificação | Autorização por contexto, rate limit e respostas mínimas |
| Dependência vulnerável | Comprometimento da aplicação | SBOM, varredura e atualização contínua |
| Auditoria insuficiente | Falha de investigação | Eventos de acesso detalhados e armazenamento inviolável |

## Limitações relevantes

A API não possui autenticação, autorização, criptografia de aplicação, gestão de
consentimento, segregação por instituição, anonimização formal ou política de retenção.
Ela deve permanecer restrita a ambiente local e dados sintéticos. O tratamento real
de dados de saúde exige avaliação jurídica, de segurança e de governança adequada ao
contexto, incluindo a legislação aplicável.
