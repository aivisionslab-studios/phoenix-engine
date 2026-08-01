# Changelog — AIVisions Phoenix Engine

Este arquivo documenta mudanças relevantes do projeto, seguindo a metodologia de **Errata Evolutiva**: correções e mudanças que quebram compatibilidade são registradas de forma transparente, não silenciosamente sobrescritas.

## [Não lançado]

### Corrigido
- Checagem de prontidão do `settings.yml` do SearXNG (chave `server:`/`secret_key:` em vez de `formats:`);
- Patch de configuração do SearXNG usando inserção idempotente de blocos em vez de descomentar linhas inexistentes;
- Substituição regex mal escapada gravando barras invertidas literais no `settings.yml` — corrigido com função lambda de substituição;
- Erro de Execution Policy do Windows bloqueando o instalador — resolvido com lançador `Instalar_Phoenix.bat`;
- Bug do `ProvisioningEngine` restrito a `winget` sem fallback Linux — resolvido com `AptConnector`;
- Bug do `ServicesEngine` sem `event_bus`;
- Regressão no roteamento Ollama/download do `llama_cpp.py` causada por versão externa que melhorava descoberta de caminhos mas removia as regras de roteamento — mesclado mantendo ambas as melhorias.

### Adicionado
- `gpu_split.py` — calculadora de split GPU/CPU/híbrido baseada em header GGUF e VRAM real;
- Agente residente completo (Intent → Research → Decision → Approval → Execute) portado para `intelligence/`;
- `HardwareDiscoveryAdapter` como drop-in para `HardwareBridge`, com fallback automático;
- Integração do `HardwareTelemetryCore` do pacote `hardware_engine` no `HardwareDiscoveryAdapter`.

### Removido
- Código órfão: `phoenix_kernel/core/event_bus.py`, `phoenix_kernel/contracts/`, `13_resident/resident_manager.py` quebrado.

### Segurança
- Incidente identificado: `data/firebase_service_account.json` (chave privada real) incluído indevidamente em um pacote enviado fora do controle de versão. Recomendação: rotacionar a chave no console do Firebase.

## Itens conhecidos em aberto
- API mismatch em `HardwareDiscoveryCore` (modelo de scan contínuo substituindo `discover()`/`load()` discretos);
- Erro `"name 'MissionAction' is not defined"` ao processar comando de missão via `POST /api/command` — import faltando, ainda não investigado.
