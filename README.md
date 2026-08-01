# 🔥 Phoenix Engine

```
██████╗ ██╗  ██╗ ██████╗ ███████╗███╗   ██╗██╗██╗  ██╗
██╔══██╗██║  ██║██╔═══██╗██╔════╝████╗  ██║██║╚██╗██╔╝
██████╔╝███████║██║   ██║█████╗  ██╔██╗ ██║██║ ╚███╔╝
██╔═══╝ ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║██║ ██╔██╗
██║     ██║  ██║╚██████╔╝███████╗██║ ╚████║██║██╔╝ ██╗
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝
```

**AIVisionsLab Studio Group · Local AI Orchestration Platform · 2026**

*"Hardware não morre — só espera o software certo."*

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
![Backend](https://img.shields.io/badge/Backend-Vulkan%20%7C%20CPU-red)
![OS](https://img.shields.io/badge/OS-Windows%2010%2F11%20%7C%20Ubuntu%20%7C%20Debian-blue)
![Status](https://img.shields.io/badge/Status-Em%20desenvolvimento%20ativo-yellow)

---

## O que é o Phoenix Engine

A Phoenix não compete com llama.cpp, Ollama, ComfyUI ou OpenWebUI.

Ela opera **uma camada acima**: detecta o hardware da máquina, entende o que ele consegue executar, provisiona a stack correta, e mantém tudo rodando — sem que o usuário precise saber uma única flag de compilação.

```
Usuário ──► Clica em "Iniciar_Phoenix"

Phoenix ──► Garante Git (bootstrap)
        ──► Escaneia todos os discos, escolhe o mais rápido com espaço
        ──► Detecta hardware (CPU, GPU, VRAM, RAM)
        ──► Provisiona dependências do SO (winget / apt)
        ──► Clona e compila os motores de inferência
        ──► Sobe containers, cria atalhos, roda self-tests
        ──► Ambiente pronto
```

O projeto nasceu de testes reais com uma AMD RX 580 8GB de 2017, executando LLMs e geração de imagem via Vulkan em 2026 — sem CUDA, sem ROCm, sem nuvem. O guia técnico completo dessa prova está em [rx580-local-ai-guide](https://github.com/aivisionslab-studios/rx580-local-ai-guide). A Phoenix é o próximo passo: transformar esse conhecimento específico em uma plataforma que se adapta a qualquer hardware.

---

## Índice

- [Hardware de referência](#hardware-de-referência-testado)
- [Arquitetura](#arquitetura)
- [Componentes principais](#componentes-principais)
- [Dashboard — Mission Control](#dashboard--mission-control)
- [App Store — Missões](#app-store--missões)
- [Catálogo de modelos por hardware](#catálogo-de-modelos-por-hardware)
- [Quick Start](#quick-start)
- [Windows](#windows)
- [Linux (Ubuntu / Debian)](#linux-ubuntu--debian)
- [O que o instalador faz, passo a passo](#o-que-o-instalador-faz-passo-a-passo)
- [Repos de terceiros](#repos-de-terceiros)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Créditos](#créditos)
- [Licença](#licença)

---

## Hardware de referência (testado)

| Componente | Especificação |
|---|---|
| CPU | Intel Xeon E5-2690 v3 · 12c/24t · 3.5GHz (2014) |
| GPU | AMD Radeon RX 580 2048SP · 8GB GDDR5 (Polaris/GCN4) |
| RAM | 32GB DDR4 REG ECC Quad Channel |
| Storage | NVMe + HDD (o instalador escolhe automaticamente o disco mais rápido com espaço suficiente) |
| Backends | CPU, Vulkan |
| OS | Windows 10/11 + WSL2 Ubuntu 22.04 / Ubuntu 26.04 LTS |
| Vulkan SDK | 1.4.341.1 |
| Driver AMD | 31.0.21924.61 |

> A Phoenix não é exclusiva para esse hardware. Foi desenhada para classificar e se adaptar a qualquer combinação de CPU/GPU/RAM. Esse é o ambiente onde é desenvolvida e validada primeiro.

---

## Arquitetura

A Phoenix opera como um **orquestrador puro**. Ela não reimplementa inferência — ela detecta, decide, configura e consome ferramentas já consolidadas como módulos plugáveis.

```
                    ┌─────────────────────┐
                    │   Hardware Scanner   │
                    │  CPU · GPU · VRAM    │
                    │  RAM · Storage       │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Classification      │
                    │  GPU Score           │
                    │  Machine Class       │
                    │  LOW / MEDIUM / HIGH │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Model Catalog      │
                    │  Recomendação por    │
                    │  tier de hardware    │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼───────────────┐
              ▼                ▼               ▼
        llama.cpp /      stable-diffusion   whisper.cpp
          Ollama              .cpp
       (chat / coder)      (imagens)        (áudio)
              │                │               │
              └────────────────┴───────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Mission Control    │
                    │   Dashboard Web      │
                    │   localhost:8000     │
                    └─────────────────────┘
```

A decisão de qual backend usar (Vulkan, CPU, híbrido) é feita automaticamente com base no hardware detectado. O usuário vê o resultado — não o processo.

**Política de roteamento de hardware (definitiva):** modelos de texto (LLM/chat) rodam 100% em CPU via llama.cpp; modelos de imagem (SD/FLUX) rodam 100% em GPU via stable-diffusion.cpp/Vulkan. Isso evita as duas cargas disputarem VRAM ao mesmo tempo.

---

## Componentes principais

| Módulo | Responsabilidade |
|---|---|
| `api_server.py` | Backend FastAPI — API principal da plataforma |
| `phoenix_kernel/` | Núcleo da plataforma |
| `phoenix_kernel/discovery/` | Detecção de hardware (Windows: WMI/HardwareMonitor · Linux: lspci/lsblk/sysfs) |
| `phoenix_kernel/telemetry/` | Telemetria ao vivo — temperatura, carga, VRAM, fans |
| `phoenix_kernel/models/` | Catálogo, compatibilidade hardware/modelo, downloads |
| `phoenix_kernel/planner/` | Planejamento de missões e RAG |
| `phoenix_kernel/runtime/` | Execução dos motores de IA |
| `phoenix_kernel/resident/` | Gerente Residente — análise e decisão autônoma |
| `phoenix_kernel/services/` | Serviços auxiliares e provisioning (inclui `ocr_engine.py` — Tesseract nativo) |
| `phoenix_kernel/security/` | Regras de segurança |
| `phoenix_kernel/logs/` | Motor de eventos (histórico recente, comando `logs`) |
| `phoenix_kernel/api/` | Dispatcher de comandos (`process_command`) usado pela API |
| `core/` | Núcleo base compartilhado |
| `install/` | Instaladores multiplataforma (PowerShell) |
| `web/` | Dashboard Mission Control |
| `platform_source/` | Phoenix Aviary — interface de inferência |
| `catalog/` | Catálogo de modelos e regras de recomendação |
| `assets/` | Ícones da aplicação (`.ico` Windows / `.png` Linux) |

---

## Dashboard — Mission Control

O Phoenix Engine roda um dashboard local (`localhost:8000`) com:

- **System Tuner** — CPU, RAM, GPU, VRAM, backends disponíveis, GPU Score e Machine Class em tempo real
- **Environment** — status de Docker, Python, Vulkan SDK, Ollama
- **Inference** — modelo ativo, uso de VRAM, temperatura e carga da GPU ao vivo
- **Phoenix Status** — documentos indexados no RAG, safety rules, estado do planner
- **Hardware Devices** — inventário completo de dispositivos e sensores (accordion por dispositivo)
- **System Telemetry** — gráfico ao vivo de CPU/GPU load
- **Terminal Deck** — interface de comando (`phoenix> infer <pergunta>`, `phoenix> ocr <caminho da imagem>`, `phoenix> search <busca>`)

---

## App Store — Missões

Em vez de instalar peça por peça, a Phoenix oferece **missões**: pacotes coerentes de ferramentas + modelos para um objetivo específico.

| Missão | O que provisiona | Tempo | Tamanho |
|---|---|---|---|
| 🧠 Assistente Pessoal | LLM + RAG para estudos e produtividade | 20–40 min | 15 GB |
| 💬 Conversar com IA | Stack completa de chat local | 15–30 min | 10 GB |
| 🖥️ Modo CPU Only | Para máquinas sem GPU dedicada | 10 min | 5 GB |
| 💻 Ambiente Dev | Ferramentas de programação + IA | 15–20 min | 10 GB |
| 🎨 Criar Imagens | Geração de imagens + workflows | 20–40 min | 25 GB |
| 🔍 Pesquisa Inteligente | Busca privada + RAG local | 10–15 min | 5 GB |
| 🎙️ Studio de Voz Offline | STT, TTS e clonagem de voz | 15–20 min | 8 GB |
| 🚀 Plataforma Completa | Tudo que o hardware suporta | 60+ min | 50+ GB |
| ⚡ RX 580 Revival | Otimizado para Polaris/GCN4 via Vulkan | 20–30 min | 15 GB |

---

## Catálogo de modelos por hardware

A Phoenix classifica o hardware detectado e recomenda modelos compatíveis — sem tentativa e erro:

```
VRAM detectada: 8192 MB
Machine Class: MEDIUM
GPU Score: 94%

Modelos recomendados:
★★★★★ qwen3:8b           — assistente geral, cabe 100% em VRAM
★★★★★ gemma3:4b          — muito rápido, baixo consumo
★★★★☆ qwen2.5-coder:7b   — programação
★★★★☆ llama3.2:3b        — uso geral / português

Modelos híbridos (VRAM + RAM):
★★★☆☆ deepseek-r1:14b    — raciocínio, offload parcial necessário

Não recomendado para este hardware:
✗ qwen3:30b
✗ llama3.3:70b
✗ deepseek-r1:671b
```

O catálogo completo (regras de classificação, VRAM mínima, estratégia de offload) vive em [`catalog/`](./catalog).

---

## Quick Start

### Windows

```powershell
git clone https://github.com/aivisionslab-studios/phoenix-engine.git
cd phoenix-engine
```

Dê **dois cliques em `Iniciar_Phoenix.bat`** (ou "Executar como Administrador" — recomendado). Ele detecta sozinho se é a primeira execução: se não houver ambiente virtual ainda, roda o instalador completo primeiro; se já existir, sobe a API direto. Depois de rodar uma vez, um atalho **Phoenix Engine** aparece na Área de Trabalho e no Menu Iniciar — clique nele nas próximas vezes.

### Linux (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/aivisionslab-studios/phoenix-engine.git
cd phoenix-engine
sudo pwsh ./install_phoenix.ps1
```

Depois de instalado, use `./Iniciar_Phoenix.sh` (ou o ícone criado no menu de aplicativos / Área de Trabalho) para subir a API nas próximas vezes, sem reprovisionar tudo de novo.

Nos dois casos, ao final: **http://localhost:8000**

---

## Windows

Compatível com **Windows 10 e Windows 11**.

O bootstrap (`install_phoenix.ps1`) garante **Git** via winget como primeiro passo — antes de qualquer outra coisa, inclusive antes de confirmar PowerShell 7. Se o ambiente ainda estiver no Windows PowerShell 5.1 nesse ponto, o instalador reconhece isso automaticamente (PS 5.1 só existe no Windows) e segue mesmo assim em modo degradado, em vez de travar.

O `install/windows.ps1` então usa **winget** para provisionar, por categoria:

| Categoria | Pacotes |
|---|---|
| CORE | Docker Desktop, PowerShell 7, .NET SDK 9.0, Node.js LTS |
| BUILD | Visual Studio Build Tools, Vulkan SDK |
| AI | LM Studio |
| UTILITIES | FFmpeg, Tesseract OCR, PowerToys, GitHub Desktop, VLC, Firefox, Chrome |

Além disso, configura o Windows: habilita WSL2 e Virtual Machine Platform (se ainda não estiverem), verifica virtualização VT-x/AMD-V e suporte a AVX2, libera as portas oficiais da Phoenix no Firewall, habilita Developer Mode e Long Paths (necessário pros 45+ repositórios clonados), e ajusta a Execution Policy.

Ao final, roda 6 self-tests (Python, Docker, HardwareMonitor, GPU Sensors, Vulkan, LM Studio CLI) e cria os atalhos de Desktop/Menu Iniciar.

Sensores de hardware lidos via **LibreHardwareMonitor** (pythonnet) — é tratado como componente **primordial**: se a instalação dele falhar, o provisionamento inteiro para (não é só um aviso), porque sem ele a Phoenix não enxerga a GPU.

```powershell
# Recomendado: clique com o botão direito em Iniciar_Phoenix.bat -> "Executar como administrador"
.\Iniciar_Phoenix.bat
```

---

## Linux (Ubuntu / Debian)

Compatível com **Ubuntu 24.04+**, **Ubuntu 26.04 LTS** e **Debian 12+** (qualquer distro baseada em `apt-get`).

O instalador usa **PowerShell 7** como camada de automação multiplataforma — precisa rodar como root (`sudo pwsh`), porque provisiona pacotes de sistema. O `install/linux.ps1` provisiona via apt:

```
git (via bootstrap, antes do resto)
docker.io · docker-compose-v2 · build-essential
python3 · python3-venv · python3-pip
vulkan-tools · mesa-vulkan-drivers (RADV)
cmake · ffmpeg · tesseract-ocr
nodejs · npm · lm-sensors · pciutils
```

Instalação:

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/aivisionslab-studios/phoenix-engine.git
cd phoenix-engine
sudo pwsh ./install_phoenix.ps1
```

Ao final, cria um atalho `.desktop` no menu de aplicativos e (se existir) na Área de Trabalho — resolvendo o usuário real por trás do `sudo` (via `SUDO_USER`), não o `root`, e respeitando o nome localizado da pasta (`~/Área de Trabalho` em PT-BR, não só `~/Desktop`).

Sensores de hardware lidos via **/proc**, **/sys**, **lm-sensors**, **lspci** e **lsblk**. GPU AMD com driver Mesa RADV expõe temperatura e VRAM via sysfs.

Validar Vulkan após instalação:

```bash
vulkaninfo --summary
```

Resultado esperado com RX 580:

```
GPU0: AMD Radeon RX 580 | DRIVER_ID_MESA_RADV | driverInfo: Mesa 26.x
```

---

## O que o instalador faz, passo a passo

1. **Git** — garantido primeiro, via winget/apt, antes de qualquer outra dependência (nada mais funciona sem ele).
2. **PowerShell 7** — verifica e instala se preciso; se não conseguir confirmar o upgrade, segue em modo degradado em vez de travar.
3. **Scanner de armazenamento** — escaneia todos os discos (`NVMe`/`SSD`/`HDD` reais, não por suposição de barramento), escolhe o mais rápido com pelo menos 40GB livres; se nenhum tiver, cai pro HDD com mais espaço como último recurso. Identifica o disco de sistema sozinho (`IsBoot` no Windows / mountpoint `/` no Linux) — nunca assume letra de unidade fixa.
4. **Camada específica do SO** — Windows (winget) ou Linux (apt), categorizada, com self-tests e atalhos de Desktop/Menu.
5. **Camada comum** — cria o venv Python, clona os 45+ repositórios do ecossistema Aviary, compila o llama.cpp com Vulkan nativo, sobe os containers Docker (Ollama, Open WebUI, SearXNG), inicia o Phoenix Studio (Node.js) e a `api_server.py`.

Se qualquer etapa exigir reinício (ex: Docker Desktop recém-instalado, WSL2 recém-habilitado), o instalador para ali, avisa, e pede pra rodar de novo depois do reinício — em vez de seguir tentando usar algo que ainda não terminou de subir.

---

## Repos de terceiros

A Phoenix **não versiona nem distribui** código de terceiros. Ela clona diretamente das fontes oficiais durante o provisionamento (`common.ps1`). Cada projeto mantém sua própria licença. Alguns dos 45+ clonados:

| Categoria | Projetos |
|---|---|
| Runtime de Inferência | [llama.cpp](https://github.com/ggml-org/llama.cpp), [Ollama](https://github.com/ollama/ollama), [vLLM](https://github.com/vllm-project/vllm), [KoboldCpp](https://github.com/LostRuins/koboldcpp), [LocalAI](https://github.com/mudler/LocalAI), [ExLlamaV2](https://github.com/turboderp-org/exllamav2), [MLC-LLM](https://github.com/mlc-ai/mlc-llm), [SGLang](https://github.com/sgl-project/sglang) |
| Geração de Imagem | [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp), [ComfyUI](https://github.com/comfyanonymous/ComfyUI), [Automatic1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui), [Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge), [InvokeAI](https://github.com/invoke-ai/InvokeAI), [SwarmUI](https://github.com/mcmonkeyprojects/SwarmUI) |
| Áudio | [whisper.cpp](https://github.com/ggml-org/whisper.cpp), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [Piper](https://github.com/rhasspy/piper), [Coqui-TTS](https://github.com/idiap/coqui-ai-TTS), [Kokoro](https://github.com/hexgrad/kokoro), [Applio](https://github.com/IAHispano/Applio) |
| Interfaces | [OpenWebUI](https://github.com/open-webui/open-webui), [LibreChat](https://github.com/danny-avila/LibreChat), [SillyTavern](https://github.com/SillyTavern/SillyTavern), [LobeChat](https://github.com/lobehub/lobe-chat), [Big-AGI](https://github.com/enricoros/big-AGI) |
| Agentes / AI OS | [CrewAI](https://github.com/crewAIInc/crewAI), [AutoGen](https://github.com/microsoft/autogen), [LangGraph](https://github.com/langchain-ai/langgraph), [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter), [OpenHands](https://github.com/All-Hands-AI/OpenHands) |
| Hardware (Windows) | [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) — componente primordial, clonado só no Windows |
| Busca | [SearXNG](https://github.com/searxng/searxng) — não clonado, roda via Docker |

Lista completa e sempre atualizada: [`install/common.ps1`](./install/common.ps1) (dicionário `$Repos`).

---

## Estrutura do repositório

```
phoenix-engine/
│
├── install_phoenix.ps1        # Bootstrap: Git -> PS7 -> Storage -> SO -> Common
├── Iniciar_Phoenix.bat        # Launcher unico Windows (instala se precisar, senao so inicia)
├── Iniciar_Phoenix.sh         # Launcher de uso diario Linux
│
├── install/
│   ├── storage_scanner.ps1    # Escaneia discos, escolhe o melhor, identifica disco de sistema
│   ├── windows.ps1            # Provisionamento Windows 10/11 (winget, categorizado)
│   ├── linux.ps1               # Provisionamento Ubuntu/Debian (apt)
│   ├── common.ps1              # Camada comum (venv, 45+ repos, compilacao, containers)
│   └── powershell.ps1          # Garante PowerShell 7
│
├── assets/
│   ├── phoenix_engine.ico     # Icone Windows (Desktop/Menu Iniciar)
│   └── phoenix_engine.png     # Icone Linux (.desktop)
│
├── phoenix_kernel/
│   ├── kernel.py               # Boot e orquestracao (Composition Root)
│   ├── discovery/              # Deteccao de hardware
│   ├── telemetry/              # Sensores ao vivo
│   ├── models/                 # Catalogo e gerenciamento de modelos
│   ├── planner/                # Planejamento e RAG
│   ├── runtime/                # Execucao dos motores de IA
│   ├── resident/                # Gerente Residente autonomo
│   ├── services/
│   │   ├── engine.py            # ServicesEngine
│   │   └── ocr_engine.py        # OCR nativo via Tesseract
│   ├── security/                # Regras de seguranca
│   ├── logs/                    # Motor de eventos (comando "logs")
│   ├── api/
│   │   └── engine.py             # Dispatcher de comandos (process_command)
│   └── core/                    # Tipos e enums base
│
├── core/                       # Nucleo base compartilhado
├── catalog/                    # Catalogo de modelos e pacotes
├── web/                        # Dashboard Mission Control
├── platform_source/            # Phoenix Aviary Platform
├── data/                       # Estado local (nao versionado)
├── docs/                       # Documentacao de arquitetura
├── tools/                      # Scripts auxiliares
├── api_server.py               # Backend FastAPI
├── setup_environment.py        # Setup do ambiente Python
├── LICENSE.md
└── README.md
```

---

## Troubleshooting

**Dashboard não sobe em `localhost:8000`**
Confirme que `api_server.py` está rodando e que a porta não está em uso.

**"Sistema operacional nao suportado" logo no início, no Windows**
Sintoma de o upgrade automático pro PowerShell 7 não ter completado (ex: winget do PS7 falhou silenciosamente). O `install_phoenix.ps1` atual já trata esse caso — se ainda estiver no PS 5.1 depois da tentativa, segue em modo degradado em vez de travar. Se persistir, confirme manualmente: `winget install Microsoft.PowerShell` e rode `pwsh ./install_phoenix.ps1` direto.

**GPU não aparece no System Tuner (Windows)**
O processo precisa ser executado como Administrador — sensores de GPU via LibreHardwareMonitor exigem elevação. Rode `Iniciar_Phoenix.bat` como Admin. Se a instalação do LibreHardwareMonitor falhar, o instalador para com erro (é tratado como componente primordial, não apenas um aviso).

**GPU não aparece no System Tuner (Linux)**
Confirme que o driver Mesa RADV está instalado: `vulkaninfo --summary`. Para temperatura, verifique se lm-sensors está configurado: `sensors`.

**`ModuleNotFoundError: No module named 'phoenix_kernel.logs'` (ou qualquer outro submódulo)**
Confirme se essa pasta não está sendo capturada por engano pelo `.gitignore`. Um padrão como `logs/` (sem `/` na frente) ignora **qualquer** pasta chamada `logs` no repositório inteiro, não só a da raiz — inclusive `phoenix_kernel/logs/`. Rode `git check-ignore -v phoenix_kernel/logs/engine.py` pra confirmar, e ancore o padrão com `/logs/` no `.gitignore` se for o caso.

**RAG mostrando 0 documentos**
O arquivo `data/knowledge_base.json` precisa existir. O índice vetorial (`data/chroma_db/`) é gerado localmente a partir dele e não vem no clone.

**Ícone de Desktop não aparece (Linux)**
O instalador roda como root via `sudo`, então precisa resolver o usuário real via `$SUDO_USER` — se você rodou como root "de verdade" (não via sudo, ex: já logado como root), o instalador usa `$HOME` atual e avisa no log. Confirme rodando `sudo pwsh ./install_phoenix.ps1` como usuário normal, não logado direto como root.

**Docker não consegue alcançar llama-server ou sd-server**
Windows Defender bloqueia a subnet Docker (172.x.x.x) por padrão. O instalador já libera as portas oficiais da Phoenix automaticamente (seção de configuração do Windows); se precisar liberar manualmente:
```powershell
New-NetFirewallRule -DisplayName "Phoenix AI Services" `
  -Direction Inbound -Protocol TCP -LocalPort 8081,7860 -Action Allow
```

---

## Roadmap

**Implementado**

- ✅ Kernel modular com boot sequence
- ✅ Discovery Engine (Windows + Linux)
- ✅ Telemetria ao vivo com sensores reais
- ✅ Runtime Engine (llama.cpp, Ollama, stable-diffusion.cpp, whisper.cpp)
- ✅ Planner + RAG local
- ✅ Gerente Residente
- ✅ App Store — Missões
- ✅ Dashboard Mission Control com accordion de sensores
- ✅ OCR nativo via Tesseract (comando `ocr`)
- ✅ Instalador multiplataforma (Windows 10/11 + Ubuntu/Debian) com bootstrap de Git, fallback PS 5.1 e self-tests
- ✅ Scanner de armazenamento com prioridade NVMe > SSD > HDD e detecção automática de disco de sistema
- ✅ Atalhos automáticos de Desktop/Menu Iniciar (Windows) e `.desktop` (Linux)
- ✅ Vulkan backend RX 580 / Polaris

**Próximos**

- Rota HTTP `/api/ocr` real no `api_server.py` (upload de imagem direto do chat)
- Execution Guard — aprovação visual antes de instalar
- Auto-tuning de modelos por benchmark real
- Hardware Service centralizado com cache de snapshot
- Phoenix Knowledge Cloud — telemetria agregada
- Release pública estável

---

## Créditos

Projeto do **AIVisionsLab Studio Group**. Construído sobre o trabalho de [ggerganov](https://github.com/ggerganov) (llama.cpp, whisper.cpp), [leejet](https://github.com/leejet) (stable-diffusion.cpp), e as comunidades de Ollama, OpenWebUI e ComfyUI.

A prova de conceito original — LLM + imagem via Vulkan no RX 580, sem CUDA — foi documentada por [艾米心 Amihart](https://medium.com/@amihart) (primeiro LLM via Vulkan no RX 580, Jan 2025) e [DadHacks](https://dadhacks.org) (stable-diffusion.cpp via Vulkan, Dez 2025).

---

## Licença

**Creative Commons Atribuição-NãoComercial 4.0 Internacional (CC BY-NC 4.0)**

Copyright © 2026 AIVisionsLab Studio Group — Creative & Tech Solutions

Uso livre para fins pessoais e educacionais com atribuição. Uso comercial requer autorização expressa por escrito.

A Phoenix não distribui nem embute software de terceiros — ela automatiza a instalação diretamente das fontes oficiais. Cada ferramenta mantém sua própria licença original.

Texto completo: [`LICENSE.md`](./LICENSE.md) · [creativecommons.org/licenses/by-nc/4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.pt-BR)

---

*Construído em São Paulo, Brasil 🇧🇷*
