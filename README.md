# 🔥 Phoenix Engine

```
██████╗ ██╗  ██╗ ██████╗ ███████╗███╗   ██╗██╗██╗  ██╗
██╔══██╗██║  ██║██╔═══██╗██╔════╝████╗  ██║██║╚██╗██╔╝
██████╔╝███████║██║   ██║█████╗  ██╔██╗ ██║██║ ╚███╔╝
██╔═══╝ ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║██║ ██╔██╗
██║     ██║  ██║╚██████╔╝███████╗██║ ╚████║██║██╔╝ ██╗
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝
```

**AIVisionsLab · Hardware Revival Platform · 2026**

*"Hardware não morre — só espera o software certo."*

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
![Backend](https://img.shields.io/badge/Backend-Vulkan-red)
![OS](https://img.shields.io/badge/OS-Windows%20%7C%20Linux-blue)
![Status](https://img.shields.io/badge/Status-Em%20desenvolvimento%20ativo-yellow)

---

## O que é o Phoenix Engine

O **Phoenix Engine** é a plataforma que orquestra, instala e configura automaticamente uma stack completa de IA local — LLMs, geração de imagem, transcrição de áudio, RAG — com base no hardware real detectado na sua máquina. Não é um instalador genérico: ele lê CPU, GPU, VRAM e RAM disponíveis e recomenda (ou já baixa) apenas o que o seu hardware consegue rodar bem.

Ele nasceu do mesmo projeto que provou que uma **AMD RX 580 de 2017** roda IA de ponta em 2026 via Vulkan, sem ROCm e sem CUDA — veja o guia técnico completo em [`rx580-local-ai-guide`](https://github.com/aivisionslab-studios/rx580-local-ai-guide). O Phoenix Engine é o próximo passo: transformar aquele conhecimento manual, testado à exaustão num único hardware, em uma plataforma que se adapta a qualquer máquina.

```
Hardware detectado  ──►  Classificação (GPU Score / Machine Class)  ──►  Missões recomendadas  ──►  Stack instalada e rodando
```

---

## Índice

- [Hardware de referência (testado)](#hardware-de-referência-testado)
- [Arquitetura](#arquitetura)
- [Dashboard e Mission Control](#dashboard-e-mission-control)
- [AIVisions App Store — Missões](#aivisions-app-store--missões)
- [Catálogo de modelos por hardware](#catálogo-de-modelos-por-hardware)
- [Quick Start](#quick-start)
- [Repos de terceiros](#repos-de-terceiros)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Troubleshooting](#troubleshooting)
- [Roadmap / Status](#roadmap--status)
- [Créditos](#créditos)
- [Licença](#licença)

---

## Hardware de referência (testado)

| Componente | Especificação |
|---|---|
| CPU | Intel Xeon E5-2690 v3 (Family 6, Model 63) |
| GPU | AMD Radeon RX 580 2048SP · 8GB GDDR5 (Polaris/GCN4) |
| RAM | 32GB (32608 MB) |
| Backends | CPU, Vulkan |
| OS | Windows 11 / Ubuntu 26.04 LTS (dual-boot) |

> O Phoenix Engine não é exclusivo pra esse hardware — ele foi desenhado pra classificar e se adaptar a qualquer combinação de CPU/GPU/RAM. Essa é só a máquina onde ele é desenvolvido e validado primeiro.

---

## Arquitetura

O Phoenix Engine opera como um **orquestrador puro**: ele não reimplementa inferência, ele detecta hardware, classifica capacidade, e configura/consome ferramentas já consolidadas (llama.cpp, Ollama, stable-diffusion.cpp, whisper.cpp, OpenWebUI, ComfyUI) como módulos plugáveis.

```
                    ┌─────────────────────┐
                    │   Hardware Scanner    │
                    │ (CPU / GPU / VRAM /   │
                    │  RAM / Storage)        │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Classification Engine │
                    │  GPU Score · Machine    │
                    │  Class (LOW/MEDIUM/HIGH)│
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Model Catalog        │
                    │  (recomendação por      │
                    │   tier de hardware)      │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        Ollama / llama.cpp  stable-diffusion.cpp  whisper.cpp
           (chat/coder)         (imagens)         (áudio)
              │                │                │
              └────────────────┴────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Mission Control /    │
                    │   Dashboard Web         │
                    │   (localhost:8000)       │
                    └───────────────────────┘
```

**Componentes principais:**

| Módulo | Responsabilidade |
|---|---|
| `core/` | Orquestrador, detecção de hardware, lógica de missões |
| `catalog/` | Catálogo de modelos e regras de recomendação por hardware |
| `phoenix_kernel/` | Núcleo de execução — planner, RAG, safety rules |
| `web/` | Dashboard web (Mission Control, System Tuner, Terminal Deck) |
| `api_server` | Backend da API consumida pelo dashboard |
| `install_phoenix` | Instalador — resolve e baixa dependências de terceiros |

---

## Dashboard e Mission Control

O Phoenix Engine roda um dashboard local (`localhost:8000`) com:

- **System Tuner** — CPU, RAM, GPU, VRAM, backends disponíveis, GPU Score e Machine Class detectados em tempo real
- **Environment** — status de Docker, Python, Vulkan SDK, Ollama API
- **Inference** — seleção de modelo ativo, uso de VRAM, temperatura e carga da GPU ao vivo
- **Phoenix Status** — documentos indexados no RAG, safety rules, estado do planner
- **Hardware Devices** — inventário completo de dispositivos e sensores detectados
- **System Telemetry** — gráfico ao vivo de CPU/GPU load
- **Terminal Deck** — interface de chat/comando (`phoenix> infer <pergunta>`)

---

## AIVisions App Store — Missões

Em vez de pedir pra instalar peça por peça, o Phoenix Engine oferece **missões prontas**: pacotes coerentes de ferramentas + modelos pra um objetivo específico.

| Missão | O que instala | Tempo estimado | Tamanho |
|---|---|---|---|
| 🧠 Assistente Pessoal | IA para estudos e produtividade com RAG | 20–40 min | 15 GB |
| 💬 Conversar com IA | Tudo pra conversar com IA localmente | 15–30 min | 10 GB |
| 🖥️ Modo CPU Only | Para computadores sem GPU dedicada | 10 min | 5 GB |
| 💻 Ambiente Dev | Ferramentas de programação e IA | 15–20 min | 10 GB |
| 🎨 Criar Imagens | Geração de imagens e workflows | 20–40 min | 25 GB |
| 🔍 Pesquisa Inteligente | Busca na web privada e RAG local | 10–15 min | 5 GB |
| 🎙️ Studio de Voz Offline | STT, TTS e clonagem de voz local | 15–20 min | 8 GB |
| 🚀 Plataforma Completa | Instala tudo que a máquina suporta | 60+ min | 50+ GB |
| ⚡ RX 580 Revival | Otimizado especificamente para Polaris (Vulkan) | 20–30 min | 15 GB |

---

## Catálogo de modelos por hardware

O Phoenix classifica o hardware detectado e recomenda modelos compatíveis, evitando tentativa e erro:

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

O catálogo completo (regras de classificação, min VRAM, estratégia de offload) vive em [`catalog/`](./catalog).

---

## Quick Start

```powershell
git clone https://github.com/aivisionslab-studios/phoenix-engine.git
cd phoenix-engine
.\install_phoenix
```

O instalador detecta seu hardware, sugere uma missão da App Store e resolve as dependências de terceiros automaticamente (ver seção abaixo).

Depois de instalado:

```powershell
# Iniciar o dashboard
python api_server.py
# Abrir http://localhost:8000
```

---

## Repos de terceiros

O Phoenix Engine **não versiona nem distribui** código de terceiros — ele detecta, decide e automatiza a instalação diretamente das fontes oficiais. Cada projeto abaixo mantém sua própria licença original:

| Projeto | Função |
|---|---|
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | Inferência de LLM via Vulkan |
| [Ollama](https://github.com/ollama/ollama) | Runtime de modelos (containerizado) |
| [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) | Geração de imagem via Vulkan |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | Transcrição de áudio via Vulkan |
| [OpenWebUI](https://github.com/open-webui/open-webui) | Interface de chat |
| [ComfyUI](https://github.com/comfyanonymous/ComfyUI) | Workflows de geração de imagem |
| [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) | Telemetria de hardware |

Esses projetos têm suas próprias licenças — respeite-as. O `install_phoenix` os busca a partir de um manifest versionado, sempre pinado em commit/tag específico para evitar quebras por mudanças upstream.

---

## Estrutura do repositório

```
phoenix-engine/
│
├── core/                  # Orquestrador, hardware discovery, missões
├── catalog/                # Catálogo de modelos + regras de recomendação
├── phoenix_kernel/          # Planner, RAG, safety rules
├── web/                    # Dashboard (Mission Control)
├── api_server               # Backend da API
├── install_phoenix           # Instalador
├── .gitignore
├── LICENSE                   # CC BY-NC 4.0
├── pyproject.toml
└── README.md
```

---

## Troubleshooting

**Dashboard não sobe em `localhost:8000`**
Confirme que `api_server` está rodando e que a porta não está em uso por outro processo.

**GPU não aparece no System Tuner**
Verifique se o backend Vulkan está instalado e se o driver da GPU está atualizado — veja o guia detalhado de diagnóstico Vulkan em [`rx580-local-ai-guide`](https://github.com/aivisionslab-studios/rx580-local-ai-guide).

**RAG mostrando 0 documentos**
Confirme se `data/knowledge_base.json` existe — o índice vetorial (`chroma_db/`) é gerado localmente a partir dele e não vem no clone.

---

## Roadmap / Status

🚧 **Em desenvolvimento ativo.** A arquitetura está evoluindo rápido (do orquestrador puro consumindo Cores externos até o dashboard completo com Mission Control). Issues e PRs são bem-vindos, mas espere mudanças estruturais frequentes até a primeira release estável.

---

## Créditos

Projeto do **AIVisionsLab Studio Group**. Construído sobre o trabalho de [ggerganov](https://github.com/ggerganov) (llama.cpp, whisper.cpp), [leejet](https://github.com/leejet) (stable-diffusion.cpp), e as comunidades de Ollama, OpenWebUI e ComfyUI.

---

## Licença

**Creative Commons Atribuição-NãoComercial 4.0 Internacional (CC BY-NC 4.0)**

Copyright © 2026 AIVisionsLab Studio Group — Creative & Tech Solutions

Você tem permissão para usar, copiar, modificar e redistribuir este projeto livremente para fins pessoais ou educacionais, desde que dê crédito ao AIVisionsLab Studio Group com link para o repositório oficial. Uso comercial (venda, revenda ou monetização) requer autorização expressa e por escrito.

Esta licença cobre exclusivamente o código-fonte deste repositório, a arquitetura de decisão/orquestração e a documentação original do projeto. **O Phoenix Engine não distribui nem embute software de terceiros** — ele detecta, decide e automatiza a instalação de ferramentas (Docker, Ollama, llama.cpp, stable-diffusion.cpp, OpenWebUI, ChromaDB, Vulkan SDK, entre outras) diretamente de suas fontes oficiais. Cada uma permanece sob sua própria licença original.

Módulos irmãos do ecossistema AIVisions — como o **AIVisions Hardware Discovery Core** e o **AIVisions Hardware Telemetry Core** — são consumidos pela Phoenix via SDK/contrato público e têm suas próprias licenças, não cobertas por este documento.

Texto completo: [`LICENSE.md`](./LICENSE.md) · https://creativecommons.org/licenses/by-nc/4.0/deed.pt-BR

---

*Construído em São Paulo, Brasil 🇧🇷*
