# 🔥 Phoenix Engine

```
██████╗ ██╗  ██╗ ██████╗ ███████╗███╗   ██╗██╗██╗  ██╗
██╔══██╗██║  ██║██╔═══██╗██╔════╝████╗  ██║██║╚██╗██╔╝
██████╔╝███████║██║   ██║█████╗  ██╔██╗ ██║██║ ╚███╔╝
██╔═══╝ ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║██║ ██╔██╗
██║     ██║  ██║╚██████╔╝███████╗██║ ╚████║██║██╔╝ ██╗
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝
```

**AIVisionsLab Studio Group · Hardware Revival Platform · Versão 3.0 · 2026**

*"Hardware não morre — só espera o software certo."*

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
![Backend](https://img.shields.io/badge/Backend-Vulkan-red)
![OS](https://img.shields.io/badge/OS-Windows%2010%2F11%20%7C%20Ubuntu%2026.04-blue)
![Status](https://img.shields.io/badge/Status-Em%20desenvolvimento%20ativo-yellow)

---

## O que é o Phoenix Engine

O **Phoenix Engine** é a plataforma que orquestra, instala e configura automaticamente uma stack completa de IA local — LLMs, geração de imagem, transcrição de áudio, RAG — com base no hardware real detectado na sua máquina. Não é um instalador genérico: ele lê CPU, GPU, VRAM e RAM disponíveis e recomenda (ou já baixa) apenas o que o seu hardware consegue rodar bem, tanto em **Windows 10/11** quanto em **Ubuntu 26.04 LTS**.

Ele nasceu do mesmo projeto que provou que uma **AMD RX 580 de 2017** roda IA de ponta em 2026 via Vulkan, sem ROCm e sem CUDA — veja o guia técnico completo em [`rx580-local-ai-guide`](https://github.com/aivisionslab-studios/rx580-local-ai-guide). O Phoenix Engine é o próximo passo: transformar aquele conhecimento manual, testado à exaustão num único hardware, em uma plataforma multiplataforma que se adapta a qualquer máquina.

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
- [Instalação — Windows 10/11](#instalação--windows-1011)
- [Instalação — Ubuntu 26.04](#instalação--ubuntu-2604)
- [Uso diário (depois de instalado)](#uso-diário-depois-de-instalado)
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
| OS | Windows 10/11 · Ubuntu 26.04 LTS |

> O Phoenix Engine não é exclusivo pra esse hardware — ele foi desenhado pra classificar e se adaptar a qualquer combinação de CPU/GPU/RAM, em Windows ou Linux. Essa é só a máquina onde ele é desenvolvido e validado primeiro.

---

## Arquitetura

O Phoenix Engine opera como um **orquestrador puro**: ele não reimplementa inferência, ele detecta hardware, classifica capacidade, e configura/consome ferramentas já consolidadas (llama.cpp, Ollama, stable-diffusion.cpp, whisper.cpp, OpenWebUI, ComfyUI) como módulos plugáveis. A mesma arquitetura roda em Windows e Linux — o que muda é apenas o *provider* que lê o hardware nativo de cada sistema.

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
| `phoenix_kernel/` | Núcleo de execução — planner, RAG, safety rules, discovery/telemetry providers (Windows e Linux) |
| `web/` | Dashboard web (Mission Control, System Tuner, Terminal Deck) |
| `api_server.py` | Backend da API consumida pelo dashboard |
| `install/windows.ps1` | Provisionamento específico do Windows (Winget, Docker Desktop, HardwareMonitor) |
| `install/linux.ps1` | Provisionamento específico do Ubuntu (APT, Docker Engine, lm-sensors) |
| `install/common.ps1` | Camada comum — venv, dependências Python, clonagem de repositórios, containers |
| `install_phoenix.ps1` | Ponto de entrada único — detecta o SO e chama o instalador correto |

---

## Dashboard e Mission Control

O Phoenix Engine roda um dashboard local (`localhost:8000`) com:

- **System Tuner** — CPU, RAM, GPU, VRAM, backends disponíveis, GPU Score e Machine Class detectados em tempo real
- **Environment** — status de Docker, Python, Vulkan SDK, Ollama API
- **Inference** — seleção de modelo ativo, uso de VRAM, temperatura e carga da GPU ao vivo
- **Phoenix Status** — documentos indexados no RAG, safety rules, estado do planner
- **Hardware Devices** — inventário completo de dispositivos e sensores detectados (CPU, GPU, discos, placa-mãe)
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

## Instalação — Windows 10/11

### Pré-requisitos

- Windows 10 ou 11, com **PowerShell 5.1+** (já vem no sistema)
- Conta com privilégios de Administrador
- Conexão com a internet (o instalador baixa Python, Docker Desktop e outras dependências via [Winget](https://learn.microsoft.com/pt-br/windows/package-manager/winget/))
- **Git instalado antes de qualquer outra coisa.** O `windows.ps1` reinstala/atualiza o Git como parte do provisionamento, mas o Passo 1 abaixo já usa `git clone` — então numa instalação limpa do Windows (sem Git ainda) você precisa instalá-lo manualmente primeiro:

  ```powershell
  winget install --id Git.Git -e --source winget
  ```

  Feche e reabra o PowerShell depois de instalar, para o `PATH` ser atualizado.

### Passo a passo

1. **Clone o repositório** (ou baixe o ZIP e extraia):

   ```powershell
   git clone https://github.com/aivisionslab-studios/phoenix-engine.git
   cd phoenix-engine
   ```

2. **Rode o instalador principal** em um PowerShell comum (ele mesmo pede elevação de Administrador quando precisar):

   > ⚠️ **Execution Policy:** por padrão, o Windows bloqueia a execução de scripts `.ps1` não assinados digitalmente (erro `UnauthorizedAccess` / `PSSecurityException`). Antes de rodar o instalador, libere a execução **apenas para essa sessão do terminal**:
   >
   > ```powershell
   > Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   > ```
   >
   > Isso não altera nenhuma configuração permanente do sistema — vale só até você fechar essa janela do PowerShell. Se preferir liberar de forma persistente para o seu usuário, use `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` (permite scripts locais sem assinatura, mas ainda exige assinatura para scripts baixados da internet).

   ```powershell
   .\install_phoenix.ps1
   ```

   O script detecta que está no Windows e chama `install\windows.ps1`, que:
   - Garante/atualiza Python 3.12, Docker Desktop, .NET SDK, Vulkan SDK e Visual Studio Build Tools via Winget (o Git já deve estar instalado, conforme os Pré-requisitos acima)
   - Garante que o Docker Desktop esteja realmente rodando (sobe o app se necessário)
   - Instala as dependências Python específicas do Windows (`pythonnet`, `HardwareMonitor`, `wmi`, `pywin32`) — necessárias para ler os sensores de CPU/GPU/disco/placa-mãe
   - Roda um self-test dos sensores de GPU antes de prosseguir

3. Depois do provisionamento, o script chama automaticamente `install\common.ps1`, que:
   - Cria/ativa o ambiente virtual Python (`.venv`)
   - Instala as dependências comuns (`fastapi`, `uvicorn`, `chromadb`, etc.)
   - Clona/atualiza os repositórios oficiais de terceiros (llama.cpp, Ollama, ComfyUI etc.) em `repos\`
   - Sobe os containers Docker (Ollama e Open WebUI) e baixa o modelo padrão (`qwen3:8b`)
   - Inicia a Phoenix (`python api_server.py`)

4. Ao final, o navegador abre automaticamente em **http://localhost:8000**.

> ⚠️ **Importante:** se o card "Hardware Devices" do painel aparecer vazio, rode o PowerShell **como Administrador** — a leitura de sensores de placa-mãe e discos via `HardwareMonitor` exige elevação no Windows.

### Reinstalar/reparar dependências manualmente (se necessário)

```powershell
.\.venv\Scripts\pip.exe install HardwareMonitor pythonnet wmi pywin32
```

---

## Instalação — Ubuntu 26.04

### Pré-requisitos

- Ubuntu 26.04 LTS (ou derivado compatível)
- Usuário com permissão de `sudo`
- PowerShell para Linux (`pwsh`) — o instalador é escrito em PowerShell multiplataforma; se não tiver, instale antes:

  ```bash
  sudo snap install powershell --classic
  ```

### Passo a passo

1. **Clone o repositório:**

   ```bash
   git clone https://github.com/aivisionslab-studios/phoenix-engine.git
   cd phoenix-engine
   ```

2. **Rode o instalador principal** com `pwsh`:

   ```bash
   sudo pwsh ./install_phoenix.ps1
   ```

   O script detecta que está no Linux e chama `install/linux.ps1`, que:
   - Instala Python 3, Git, Docker Engine, Vulkan SDK e as ferramentas de build via `apt`
   - Garante que o serviço Docker (`systemd`) esteja ativo e habilitado
   - Instala `lm-sensors` (para telemetria de temperatura/fans) e roda `sensors-detect`
   - Prepara os pacotes necessários para leitura de hardware nativo (`lspci`, `lsblk`, `dmidecode`)

3. Em seguida, `install/common.ps1` roda a mesma camada comum do Windows (venv, dependências Python, clonagem de repositórios, containers Docker, download do modelo padrão) e inicia a Phoenix.

4. Acesse o dashboard em **http://localhost:8000** (o navegador padrão abre automaticamente, se disponível).

> ⚠️ **Importante:** para o Discovery e a Telemetria lerem corretamente discos, placa-mãe e sensores no Linux, pode ser necessário rodar comandos de leitura como usuário com permissão de `sudo` (ex.: `dmidecode` normalmente exige root). Se algum sensor aparecer como indisponível, rode `sudo sensors-detect` manualmente e reinicie a Phoenix.

### Rodar o Docker sem sudo (recomendado)

```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## Uso diário (depois de instalado)

Depois da primeira instalação completa, você não precisa rodar o instalador de novo — basta subir a API:

**Windows:**

```powershell
cd phoenix-engine
.\.venv\Scripts\Activate.ps1
python api_server.py
```

**Ubuntu:**

```bash
cd phoenix-engine
source .venv/bin/activate
python3 api_server.py
```

Em ambos os casos, o dashboard fica disponível em **http://localhost:8000**. Use `Ctrl+C` no terminal para encerrar o servidor.

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
| [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) | Telemetria de hardware (Windows) |

Esses projetos têm suas próprias licenças — respeite-as. O `install_phoenix.ps1` os busca a partir de um manifest versionado, sempre pinado em commit/tag específico para evitar quebras por mudanças upstream.

---

## Estrutura do repositório

```
phoenix-engine/
│
├── core/                     # Orquestrador, hardware discovery, missões
├── catalog/                   # Catálogo de modelos + regras de recomendação
├── phoenix_kernel/             # Planner, RAG, safety rules, discovery/telemetry providers
│   ├── 01_discovery/            # Descoberta de hardware (Windows/Linux providers)
│   └── 06_telemetry/            # Telemetria ao vivo (Windows/Linux providers)
├── web/                       # Dashboard (Mission Control)
├── install/
│   ├── windows.ps1              # Provisionamento específico do Windows
│   ├── linux.ps1                # Provisionamento específico do Ubuntu
│   └── common.ps1               # Camada comum (venv, containers, repos)
├── api_server.py                 # Backend da API
├── install_phoenix.ps1             # Instalador — ponto de entrada único
├── .gitignore
├── LICENSE.md                      # CC BY-NC 4.0
├── pyproject.toml
└── README.md
```

---

## Troubleshooting

**Dashboard não sobe em `localhost:8000`**
Confirme que `api_server.py` está rodando e que a porta não está em uso por outro processo.

**GPU não aparece no System Tuner**
Verifique se o backend Vulkan está instalado e se o driver da GPU está atualizado — veja o guia detalhado de diagnóstico Vulkan em [`rx580-local-ai-guide`](https://github.com/aivisionslab-studios/rx580-local-ai-guide).

**Card "Hardware Devices" aparece vazio (Windows)**
Rode o `api_server.py` (ou o instalador) como Administrador — a leitura de sensores via `HardwareMonitor` exige elevação no Windows. Confirme também que `HardwareMonitor` e `pythonnet` estão instalados dentro do `.venv`, não apenas no Python global.

**Sensores incompletos (Ubuntu)**
Rode `sudo sensors-detect` e reinicie a Phoenix. Alguns sensores de placa-mãe/SSD dependem de módulos de kernel específicos que o `sensors-detect` habilita.

**RAG mostrando 0 documentos**
Confirme se `data/knowledge_base.json` existe — o índice vetorial (`chroma_db/`) é gerado localmente a partir dele e não vem no clone.

---

## Roadmap / Status

🚧 **Em desenvolvimento ativo.** A arquitetura está evoluindo rápido (do orquestrador puro consumindo Cores externos até o dashboard completo com Mission Control multiplataforma). Issues e PRs são bem-vindos, mas espere mudanças estruturais frequentes até a primeira release estável.

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
