# Perguntas Frequentes — AIVisions Phoenix Engine

**A Phoenix envia meus prompts para algum servidor?**
Não. Por padrão, tudo roda local. Ver [Política de Privacidade](../legal/PRIVACY_POLICY.md).

**Preciso de GPU para usar a Phoenix?**
Não necessariamente. A Phoenix escolhe automaticamente entre execução CPU, GPU ou híbrida conforme o hardware disponível.

**A Phoenix funciona com GPUs antigas, tipo RX 580?**
Sim — essa é inclusive uma das configurações de referência validadas no projeto (ver [HARDWARE.md](./HARDWARE.md)).

**A Phoenix redistribui modelos de IA?**
Não. Ela detecta, recomenda e baixa modelos de fontes oficiais, mas cada modelo mantém sua licença original.

**Windows ou Linux?**
Ambos são suportados: Windows 10/11 e Ubuntu/Debian, com instaladores dedicados (`install/windows.ps1` / `install/linux.ps1`) a partir de um bootstrapper comum (`install_phoenix.ps1`).

**O que acontece se eu não aprovar uma ação sugerida pelo Resident Manager?**
Nada é executado. Ações de risco médio/alto sempre aguardam aprovação explícita (`aprovar`/`rejeitar`).

**A telemetria é obrigatória?**
Não. Telemetria remota (Firestore) é opt-in e desativada por padrão. Telemetria local sempre existe para alimentar o dashboard e o Resident Manager.
