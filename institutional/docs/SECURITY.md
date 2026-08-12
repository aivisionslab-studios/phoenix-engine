# Segurança — AIVisions Phoenix Engine

Documentação técnica de segurança. Para o processo de reporte de vulnerabilidades, ver [SECURITY_POLICY](../legal/SECURITY_POLICY.md).

## Princípios de segurança da arquitetura

A Phoenix nunca:
- Instala software sem autorização explícita do usuário;
- Envia arquivos privados para servidores externos;
- Abre portas de rede automaticamente sem consentimento;
- Altera regras de firewall sem confirmação;
- Acessa documentos pessoais fora do escopo declarado de uma missão.

## Camadas de proteção

1. **RiskEngine** — classifica cada ação proposta pelo Planner por nível de risco antes da execução.
2. **ContractValidator** — garante que módulos só se comunicam através de contratos públicos bem definidos, reduzindo superfície de ataque por acoplamento indevido.
3. **Fluxo de aprovação do Resident Manager** — ações de risco médio/alto exigem confirmação humana explícita.
4. **Isolamento via containers** — a maior parte da execução de modelos e serviços roda em containers Docker, isolados do sistema host.

## Execution Guard / Sandbox

Ações potencialmente destrutivas (remoção de containers, alteração de configuração de sistema) passam por uma camada de guarda de execução antes de serem efetivadas, com possibilidade de rollback.

## Permissões

O usuário mantém controle total sobre quais permissões concede à Phoenix — nenhuma ação de sistema é escalada silenciosamente.
