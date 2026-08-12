# 🦅 Phoenix Aviary Platform v3.0 & Phoenix Engine 5.0
## Manual de Operação e Documentação Técnica Completa
**Complete Technical Documentation and User Operation Manual**

---

> **Idiomas / Languages:**
> - 🇧🇷 **Português (Brasil)** - Seção 1
> - 🇺🇸 **English (US)** - Section 2

---

# 🇧🇷 SEÇÃO 1: MANUAL COMPLETO (PORTUGUÊS - BRASIL)

## 1. Visão Geral da Plataforma

A **Phoenix Aviary Platform v3.0** e o **Phoenix Engine 5.0** constituem um ecossistema completo e integrado para orquestração, execução e monitoramento de Inteligência Artificial Local e em Nuvem. O projeto permite alternar dinamicamente entre modelos locais (Ollama, LM Studio, llama.cpp / llama-server com Vulkan, vLLM) e provedores na nuvem (Google Gemini, OpenAI, Anthropic Claude).

### Principais Destaques:
- **Orquestração Multiprovedor:** Suporte a 13+ provedores de IA locais e na nuvem.
- **Aceleração por Hardware:** Suporte nativo a GPU (Vulkan, CUDA) e CPU (AVX2/AVX-512) compilados sob medida via `llama.cpp` e `stable-diffusion.cpp`.
- **Síntese de Voz Neural (TTS):** Integração com Piper TTS (`/api/tts/piper`) com suporte a modelos neurais em Português e Inglês e fallback inteligente para Web Speech API.
- **Ecossistema Completo:** Chat Interativo, Arena de Comparação Lado a Lado (Model Arena), Central de Modelos (Model Hub), Calculadora de VRAM/Hardware e Dashboard do Ecossistema.

---

## 2. Arquitetura do Sistema

A aplicação adota uma arquitetura de pilha completa (**Full-Stack**) de alto desempenho:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Phoenix Aviary Web UI (Vite + React 19)             │
│                             Porta / Port 3000                          │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTP / Websocket / REST Proxy
┌──────────────────────────────────▼─────────────────────────────────────┐
│                 Node.js / Express Server (server.ts)                   │
│                             Porta / Port 3000                          │
└────────┬─────────────────────────┬────────────────────────────┬────────┘
         │                         │                            │
┌────────▼──────────────┐ ┌────────▼─────────────┐ ┌────────────▼────────────┐
│ Google Gemini API     │ │ Phoenix Python Engine│ │ Provedores Locais         │
│ (Cloud Gemini 3.6/3.1)│ │  (api_server.py)    │ │ - Ollama (11434)          │
└───────────────────────┘ │  Porta / Port 8000   │ │ - LM Studio (1234)        │
                          └──────────┬───────────┘ │ - llama-server (8081)     │
                                     │             │ - Open WebUI (8010)       │
                               ┌─────▼─────┐       └───────────────────────────┘
                               │ Piper TTS │
                               └───────────┘
```

---

## 3. Estrutura de Diretórios e Armazenamento

A estrutura principal do ecossistema Phoenix no disco:

- `C:\AIVisions Platform\PHOENIX 3.0\` — Código-fonte da plataforma, dependências e servidor Node.js/Express.
- `R:\Phoenix\Workstations\Models\` — Diretório recomendado de armazenamento de modelos (NVMe de alta velocidade).
  - `Chat\GGUF\` — Modelos LLM GGUF (ex: `qwen3-8b-q4_k_m.gguf`, `deepseek-r1-8b.gguf`).
  - `Vision\` — Modelos de visão (ex: `MiniCPM-V-2.6`).
  - `Voice\Piper\` — Arquivos ONNX de voz do Piper TTS e dados fonéticos do eSpeak-NG.

---

## 4. Guia Detalhado de Síntese de Voz (Piper TTS & eSpeak-NG)

### 4.1 Entendendo o Módulo de Voz
O Piper TTS utiliza modelos neurais ONNX para produzir síntese de voz ultra-realista e natural sem latência de nuvem.

### 4.2 Dependência Crítica: eSpeak-NG no Windows
O Piper necessita dos dados de fonemas do eSpeak-NG (`phontab`, `phonindex`, `phondict`) para converter o texto em unidades fonéticas antes da inferência no modelo `.onnx`.

**Sintoma do Erro:**
```text
Error processing file '/usr/share/espeak-ng-data\phontab': No such file or directory.
```

### 4.3 Como Resolver Definitivamente no Windows:

1. **Instalador Oficial:** Baixe e execute o instalador do eSpeak-NG:
   - Link Direto: `https://github.com/espeak-ng/espeak-ng/releases/download/1.51/espeak-ng-X64.msi`
   - Página de Releases: `https://github.com/espeak-ng/espeak-ng/releases`

2. **Cópia Manual de Pastas (Opção Portátil):**
   - Extraia ou copie a pasta `espeak-ng-data` diretamente para o diretório do Piper:
   - Caminho: `R:\Phoenix\Workstations\Models\Voice\Piper\espeak-ng-data\`

3. **Mecanismo de Fallback Inteligente no Projeto:**
   - Caso o servidor do Phoenix Engine esteja offline ou o eSpeak-NG ainda não esteja configurado no Windows, o servidor Node.js (`server.ts`) repassa o aviso limpo e o frontend aciona automaticamente as **vozes neurais naturais do navegador (Web Speech API / Microsoft Natural Voices)** sem chiados sintéticos.

---

## 5. Provedores de IA Integrados e Portas

| Provedor | Tipo | Porta Padrão | Descrição |
|---|---|---|---|
| **Google Gemini Cloud API** | Nuvem | HTTPS (443) | Gemini 3.6 Flash, 3.1 Pro Preview, 3.1 Flash Lite |
| **Piper TTS Neural** | Local | /api/tts/piper | Síntese de voz neural PT-BR e EN-US |
| **Phoenix Python Engine** | Local | 8000 | Servidor central de gerenciamento e telemetria |
| **Ollama** | Local | 11434 | Servidor de modelos GGUF local |
| **LM Studio** | Local | 1234 | Interface gráfica e API local para modelos |
| **llama-server (llama.cpp)**| Local | 8081 | Servidor nativo de alta performance compilado em C++/Vulkan |
| **vLLM** | Local | 8000 | Servidor com PagedAttention para alto throughput |
| **Open WebUI Gateway** | Local | 8010 | Gateway proxy para pipelines de IA |
| **AnythingLLM** | Local | 3001 | Engine RAG corporativo |

---

## 6. Módulos da Interface (UI)

1. **Chat WebUI (`ChatView.tsx`):**
   - Suporte a múltiplos chats independentes.
   - Anexo de documentos e imagens com suporte a modelos Multimodais / Visão.
   - Exibição em bloco retrátil do raciocínio `<think>` do DeepSeek-R1.
   - Botão de leitura em áudio via Piper TTS com seleção de vozes masculinas e femininas em PT-BR e EN-US.

2. **Model Arena (`ArenaView.tsx`):**
   - Comparação simultânea em tempo real de até 4 modelos com o mesmo prompt.
   - Métricas de tempo de resposta, latência e saída comparativa.

3. **Model Hub (`ModelHubView.tsx`):**
   - Central de gerenciamento e atalhos de seleção de modelos locais e nuvem.

4. **VRAM & Hardware Calculator (`VramCalculatorView.tsx`):**
   - Estimador preciso de requisitos de VRAM e memória RAM conforme o tamanho dos parâmetros (7B, 14B, 32B, 70B) e quantização (Q4_K_M, Q8_0, FP16).

5. **Stack & Ecossistema (`EcosystemView.tsx`):**
   - Telemetria do sistema (Temperatura da GPU, Uso de VRAM, Carga da CPU).
   - Links diretos e guia de instalação do eSpeak-NG, Docker, WSL2 e Visual Studio Build Tools.

---

## 7. Referência de APIs Principais (`server.ts`)

- `GET /api/health` — Retorna estado de saúde, chave Gemini e estado da Phoenix Engine.
- `GET /api/engine/state` — Retorna dados em tempo real da telemetria de hardware (GPU/VRAM/CPU).
- `POST /api/gemini/chat` — Proxy seguro para chamadas à API Gemini.
- `POST /api/proxy/chat` — Proxy unificado para Ollama, LM Studio, llama-server e vLLM.
- `POST /api/tts/piper` — Rota de conversão de texto em áudio via Piper TTS com fallback seguro.

---

# 🇺🇸 SECTION 2: COMPLETE MANUAL (ENGLISH - US)

## 1. Platform Overview

**Phoenix Aviary Platform v3.0** and **Phoenix Engine 5.0** form a comprehensive ecosystem for local and cloud Artificial Intelligence orchestration, execution, and monitoring. The platform enables seamless switching between local engines (Ollama, LM Studio, llama.cpp / llama-server with Vulkan, vLLM) and cloud providers (Google Gemini, OpenAI, Anthropic Claude).

### Key Features:
- **Multi-Provider Orchestration:** Support for 13+ local and cloud AI providers.
- **Hardware Acceleration:** Native GPU acceleration (Vulkan, CUDA) and CPU optimizations (AVX2/AVX-512) via custom-built `llama.cpp` and `stable-diffusion.cpp`.
- **Neural Voice Synthesis (TTS):** Integration with Piper TTS (`/api/tts/piper`) supporting Portuguese and English neural voices with smart Web Speech API fallback.
- **Complete Suite:** Interactive Chat, Side-by-Side Model Comparison (Model Arena), Model Hub, VRAM/Hardware Calculator, and Ecosystem Dashboard.

---

## 2. System Architecture

The project employs a high-performance **Full-Stack** architecture:

- **Frontend:** Vite + React 19 SPA running on port 3000.
- **Backend Proxy Server:** Node.js Express (`server.ts`) running on port 3000.
- **Phoenix Python Engine:** FastAPI core (`api_server.py`) running on port 8000.
- **Local Runtimes:** Ollama (11434), LM Studio (1234), llama-server (8081).

---

## 3. Directory & Storage Layout

- `C:\AIVisions Platform\PHOENIX 3.0\` — Core source code, dependencies, and Express server.
- `R:\Phoenix\Workstations\Models\` — Recommended NVMe storage location for high-speed model loading.
  - `Chat\GGUF\` — LLM GGUF model files.
  - `Vision\` — Vision model encoders and weights.
  - `Voice\Piper\` — Piper ONNX neural voice files and eSpeak-NG phonetic data.

---

## 4. Voice Synthesis Setup Guide (Piper TTS & eSpeak-NG)

### 4.1 Voice Module Overview
Piper TTS relies on ONNX neural voice models to produce natural, human-like voice synthesis without cloud latency.

### 4.2 Windows Critical Dependency: eSpeak-NG
Piper requires eSpeak-NG phonetic data files (`phontab`, `phonindex`, `phondict`) to translate text into phonemes before sending it to the `.onnx` neural model.

**Error Symptom:**
```text
Error processing file '/usr/share/espeak-ng-data\phontab': No such file or directory.
```

### 4.3 Step-by-Step Resolution on Windows:

1. **Official Installer:** Download and run the official 64-bit installer:
   - Direct Download: `https://github.com/espeak-ng/espeak-ng/releases/download/1.51/espeak-ng-X64.msi`
   - Release Page: `https://github.com/espeak-ng/espeak-ng/releases`

2. **Manual Folder Copy (Portable Setup):**
   - Copy or extract the `espeak-ng-data` folder into the Piper directory:
   - Location: `R:\Phoenix\Workstations\Models\Voice\Piper\espeak-ng-data\`

3. **Smart Fallback Mechanism:**
   - If the Phoenix Engine is offline or eSpeak-NG is missing, `server.ts` cleanly notifies the client, and the frontend automatically utilizes the browser's high-quality natural voices (Web Speech API / Microsoft Natural Voices) without artificial noise.

---

## 5. Supported AI Providers and Ports

| Provider | Type | Default Port | Description |
|---|---|---|---|
| **Google Gemini Cloud API** | Cloud | HTTPS (443) | Gemini 3.6 Flash, 3.1 Pro Preview, 3.1 Flash Lite |
| **Piper TTS Neural** | Local | /api/tts/piper | Neural TTS in PT-BR and EN-US |
| **Phoenix Python Engine** | Local | 8000 | Central management & telemetry engine |
| **Ollama** | Local | 11434 | Local GGUF model runner |
| **LM Studio** | Local | 1234 | GUI and local OpenAI-compatible API |
| **llama-server (llama.cpp)**| Local | 8081 | High-performance C++/Vulkan native server |
| **vLLM** | Local | 8000 | High-throughput server with PagedAttention |
| **Open WebUI Gateway** | Local | 8010 | Proxy gateway for AI pipelines |
| **AnythingLLM** | Local | 3001 | Enterprise RAG engine |

---

## 6. UI Modules Overview

1. **Chat WebUI (`ChatView.tsx`):**
   - Multi-thread conversation management.
   - Document and image attachments with multimodal model support.
   - DeepSeek-R1 `<think>` reasoning block display.
   - Voice audio playback via Piper TTS with male/female voices in PT-BR and EN-US.

2. **Model Arena (`ArenaView.tsx`):**
   - Side-by-side live comparison of up to 4 models on a single prompt.

3. **Model Hub (`ModelHubView.tsx`):**
   - Central model library and selection shortcuts.

4. **VRAM & Hardware Calculator (`VramCalculatorView.tsx`):**
   - Accurate VRAM/RAM requirement estimator for different model parameter sizes and quantization levels.

5. **Stack & Ecosystem (`EcosystemView.tsx`):**
   - Real-time hardware telemetry dashboard (GPU Temp, VRAM Usage, CPU Load) and direct download tools.

---

## 7. Troubleshooting Guide

- **Issue:** Piper TTS throws 422 Unprocessable Entity (`phontab missing`).
  - **Solution:** Install `espeak-ng-X64.msi` or copy `espeak-ng-data` into `R:\Phoenix\Workstations\Models\Voice\Piper\`.
- **Issue:** Local provider showing "Disconnected".
  - **Solution:** Verify the local server process (e.g. Ollama or LM Studio) is active on its designated port and click "Escanear / Detectar" in the platform header.

---
*Phoenix Aviary Platform v3.0 — AI Visions Studio Group*
