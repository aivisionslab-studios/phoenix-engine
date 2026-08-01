# Política de Coleta de Dados — AIVisions Phoenix Engine

Complementa a [Política de Privacidade](./PRIVACY_POLICY.md) detalhando exatamente o que pode ser armazenado ou transmitido.

## 1. Dados que PODEM ser coletados (local, e opcionalmente enviados ao Firestore)

| Categoria | Exemplos |
|---|---|
| Hardware | CPU, GPU, VRAM, RAM, armazenamento disponível |
| Sistema | Sistema operacional, versão, drivers instalados |
| Telemetria de sensores | Temperatura, uso de CPU/GPU, uso de disco |
| Operação da Phoenix | Missões instaladas, containers ativos, logs de execução |
| Erros | Logs de falhas para diagnóstico (sem conteúdo de prompts) |

## 2. Dados que NUNCA são coletados

- ❌ Documentos pessoais
- ❌ Imagens processadas pelo usuário
- ❌ Prompts enviados a modelos de IA
- ❌ Conversas/chats
- ❌ Senhas, chaves de API ou credenciais
- ❌ Conteúdo de arquivos do sistema fora do escopo da Phoenix

## 3. Anonimização

Quando a telemetria é enviada ao Firestore (mediante opt-in), os dados são associados a um identificador técnico de instalação, **não** a dados pessoais identificáveis, salvo se o usuário fornecer voluntariamente essas informações em outro contexto (ex.: suporte).

## 4. Retenção

Dados armazenados localmente permanecem sob controle do usuário. Dados eventualmente enviados ao Firestore seguem prazos de retenção definidos para fins de melhoria de produto, podendo ser removidos mediante solicitação.
