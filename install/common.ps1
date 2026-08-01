# install/common.ps1
# Camada COMUM da Phoenix Engine - roda igual no Windows e no Linux.

# =====================================================================
# POLÍTICA DE ROTEAMENTO DE HARDWARE (DEFINITIVA)
# 1. Modelos de Chatbot/LLM (Texto) -> 100% CPU via llama.cpp (sem -ngl)
# 2. Modelos de Imagem (SD/FLUX) -> 100% GPU via stable-diffusion.cpp (Vulkan)
# =====================================================================
 $env:PHOENIX_LLM_DEVICE = "CPU"
 $env:PHOENIX_IMAGE_DEVICE = "GPU"
 $env:PHOENIX_LLM_NGL = "0"

# =====================================================================
# MAPA DE PORTAS OFICIAL DA PHOENIX 3.0 (NÃO ALTERAR SEM SINCRONIZAR)
# 3000  -> Phoenix Aviary (Frontend Node.js)
# 8000  -> Phoenix API (Backend FastAPI/Uvicorn)
# 8080  -> SearXNG API (Busca web para a IA)
# 8081  -> Llama.cpp Native Server (Servidor HTTP do motor - se ativado)
# 8088  -> SearXNG WebUI (Interface gráfica alternativa do buscador)
# 11434 -> Ollama (Docker / Fallback de CPU)
# 7860  -> Stable Diffusion Native Server (Servidor HTTP do motor Vulkan)
# 8010  -> Open WebUI (Interface legada)
# =====================================================================

if (Test-Path Variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}

if (-not (Get-Command Pause -ErrorAction SilentlyContinue)) {
    function Pause {
        Write-Host "`nPressione Enter para continuar..." -ForegroundColor DarkGray
        Read-Host | Out-Null
    }
}

Set-Location $PhoenixRoot
Write-Host "[OK] Diretorio de trabalho: $PWD" -ForegroundColor Green

 $failContract = {
    param([string]$errMsg, [string]$code)
    return @{ 
        Name="Common"; Version="N/A"; Success=$false; ErrorCode=$code; 
        Warnings=@(); Errors=@($errMsg); RestartRequired=$false; Artifacts=@(); Timestamp=Get-Date 
    }
}

if (-not (Test-Path ".\api_server.py")) {
    return (& $failContract "api_server.py nao encontrado" "PX010")
}

# 2. Ambiente virtual Python
 $VenvDir = ".venv"
 $VenvActivate = if ($IsWindows) { Join-Path $VenvDir "Scripts\Activate.ps1" } else { Join-Path $VenvDir "bin/Activate.ps1" }

if (-not (Test-Path $VenvActivate)) {
    Write-Host "[*] Criando ambiente virtual Python em $VenvDir..." -ForegroundColor Yellow
    
    $pythonExeToUse = $null
    
    if ($IsWindows) {
        $possiblePaths = @(
            "C:\Program Files\Python312\python.exe",
            "C:\Program Files\Python311\python.exe",
            "C:\Program Files\Python310\python.exe"
        )
        foreach ($path in $possiblePaths) {
            if (Test-Path $path) {
                $pythonExeToUse = $path
                Write-Host "[*] Python real encontrado em: $path" -ForegroundColor Cyan
                break
            }
        }
    }
    
    if (-not $pythonExeToUse) {
        if (Get-Command python3 -ErrorAction SilentlyContinue) { $pythonExeToUse = "python3" }
        elseif (Get-Command python -ErrorAction SilentlyContinue) { $pythonExeToUse = "python" }
    }

    if ($pythonExeToUse) {
        & $pythonExeToUse -m venv $VenvDir 2>&1 | Out-Null
    } else {
        Write-Host "[X] Python nao encontrado para criar o venv!" -ForegroundColor Red
    }
}

if (Test-Path $VenvActivate) {
    Write-Host "[*] Ativando ambiente virtual..." -ForegroundColor Cyan
    . $VenvActivate
} else {
    Write-Host "[!] Nao foi possivel criar o venv. Usando Python global." -ForegroundColor DarkYellow
}

# 3. Dependencias Python COMUNS
Write-Host "`n=== DEPENDENCIAS PYTHON COMUNS ===" -ForegroundColor Cyan
& python -m pip install --upgrade pip 2>&1 | Out-Host
& python -m pip install fastapi uvicorn psutil chromadb astor httpx google-cloud-firestore 2>&1 | Out-Host

# =====================================================================
# SCANNER DE HARDWARE (LibreHardwareMonitor via pythonnet) - COMPONENTE
# PRIMORDIAL: e o scanner que sustenta toda a deteccao de hardware da
# Phoenix (Hardware Discovery Core SDK). Mais critico que qualquer
# modelo/provider baixado depois - por isso falha AQUI, nao so avisa.
# =====================================================================
Write-Host "`n=== SCANNER DE HARDWARE (LibreHardwareMonitor) ===" -ForegroundColor Cyan

if ($IsWindows) {
    # CORREÇÃO: antes essa checagem também disparava no Linux se houvesse
    # dotnet/mono instalado - mas "wmi" e "pywin32" são pacotes Windows-only
    # e falhavam (ou instalavam stubs inúteis) em qualquer Linux.
    & python -m pip install pythonnet HardwareMonitor wmi pywin32 2>&1 | Out-Host
    $hwMonitorInstallOk = ($LASTEXITCODE -eq 0)

    if (-not $hwMonitorInstallOk) {
        return (& $failContract "Falha ao instalar o scanner de hardware (pythonnet/HardwareMonitor/wmi/pywin32). Isso e primordial - sem ele a Phoenix nao enxerga a GPU." "PX017")
    }
    Write-Host "[OK] Scanner de hardware (pythonnet + HardwareMonitor) instalado." -ForegroundColor Green
} else {
    # No Linux o scanner de sensores usa outro caminho (lm-sensors/pciutils,
    # ja garantidos no bootstrap do linux.ps1) - pythonnet/HardwareMonitor
    # sao especificos do Windows, nao se aplicam aqui.
    Write-Host "[i] Linux: scanner de hardware usa lm-sensors/pciutils (ja instalados pelo linux.ps1), nao pythonnet/HardwareMonitor." -ForegroundColor DarkGray
}

# 4. Clonagem do Ecossistema Phoenix Aviary (40+ Projetos)
Write-Host "`n=== CLONAGEM DO ECOSSISTEMA AVIARY (GIT) ===" -ForegroundColor Cyan
 $env:GIT_TERMINAL_PROMPT = "0"

 $Repos = @{
    # --- Nativos (Compilados com Vulkan) ---
    "llama.cpp"            = "https://github.com/ggml-org/llama.cpp"
    "stable-diffusion.cpp" = "https://github.com/leejet/stable-diffusion.cpp"
    "Whisper.cpp"          = "https://github.com/ggml-org/whisper.cpp"
    
    # --- Phoenix Aviary (Frontend Oficial) ---
    "phoenix_studio"       = "https://github.com/aivisionslab-studios/phoenix-studio"
    
    # --- Runtime Providers Alternativos ---
    "Ollama"               = "https://github.com/ollama/ollama"
    "vLLM"                 = "https://github.com/vllm-project/vllm"
    "KoboldCpp"            = "https://github.com/LostRuins/koboldcpp"
    "LocalAI"              = "https://github.com/mudler/LocalAI"
    "ExLlamaV2"            = "https://github.com/turboderp-org/exllamav2"
    "MLC-LLM"              = "https://github.com/mlc-ai/mlc-llm"
    "SGLang"               = "https://github.com/sgl-project/sglang"
    "text-generation-inference" = "https://github.com/huggingface/text-generation-inference"
    
    # --- Image Providers ---
    "ComfyUI"              = "https://github.com/comfyanonymous/ComfyUI"

    # --- Image Providers (adicionados - todos confirmados oficiais via busca) ---
    "stable-diffusion-webui"       = "https://github.com/AUTOMATIC1111/stable-diffusion-webui"
    "stable-diffusion-webui-forge" = "https://github.com/lllyasviel/stable-diffusion-webui-forge"
    "InvokeAI"                     = "https://github.com/invoke-ai/InvokeAI"
    "SwarmUI"                      = "https://github.com/mcmonkeyprojects/SwarmUI"
    
    # --- AI Operating Systems & Agent Frameworks ---
    "open-interpreter"     = "https://github.com/OpenInterpreter/open-interpreter"
    "OpenHands"            = "https://github.com/All-Hands-AI/OpenHands"
    "OpenDevin"            = "https://github.com/OpenDevin/OpenDevin"
    "devika"               = "https://github.com/stitionai/devika"
    "bolt.diy"             = "https://github.com/stackblitz-labs/bolt.diy"
    "continue"             = "https://github.com/continuedev/continue"
    "crewAI"               = "https://github.com/crewAIInc/crewAI"
    "autogen"              = "https://github.com/microsoft/autogen"
    "semantic-kernel"      = "https://github.com/microsoft/semantic-kernel"
    "langgraph"            = "https://github.com/langchain-ai/langgraph"
    "openai-agents-python" = "https://github.com/openai/openai-agents-python"
    
    # --- Interfaces Web e Desktop ---
    "OpenWebUI"            = "https://github.com/open-webui/open-webui"
    "LibreChat"            = "https://github.com/danny-avila/LibreChat"
    "anything-llm"         = "https://github.com/Mintplex-Labs/anything-llm"
    "lobe-chat"            = "https://github.com/lobehub/lobe-chat"
    "Flowise"              = "https://github.com/FlowiseAI/Flowise"
    "big-AGI"              = "https://github.com/enricoros/big-AGI"
    "SillyTavern"          = "https://github.com/SillyTavern/SillyTavern"
    "chatbox"              = "https://github.com/chatboxai/chatbox"
    "gpt4all"              = "https://github.com/nomic-ai/gpt4all"
    "cherry-studio"        = "https://github.com/CherryHQ/cherry-studio"
    "enchanted"            = "https://github.com/AugustDev/enchanted"
    "jan"                  = "https://github.com/janhq/jan"

    # --- Audio Providers (adicionados - todos confirmados oficiais via busca) ---
    "faster-whisper"       = "https://github.com/SYSTRAN/faster-whisper"
    "Piper"                = "https://github.com/rhasspy/piper"
    # Coqui-ai/TTS original foi descontinuado (empresa fechou em jan/2024).
    # idiap/coqui-ai-TTS e o fork ativamente mantido - cobre Coqui E XTTS
    # (XTTS e um modelo dentro desse mesmo repositorio, nao um repo separado).
    "Coqui-TTS"            = "https://github.com/idiap/coqui-ai-TTS"
    "Kokoro"               = "https://github.com/hexgrad/kokoro"
    "Applio"               = "https://github.com/IAHispano/Applio"
}

# Clona o LibreHardwareMonitor APENAS no Windows
if ($IsWindows) {
    $Repos["LibreHardwareMonitor"] = "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor.git"
}

if (-not (Test-Path ".\repos")) {
    New-Item -ItemType Directory -Force -Path ".\repos" | Out-Null
}

foreach ($repo in $Repos.Keys) {
    $dest = Join-Path ".\repos" $repo
    if (!(Test-Path $dest)) {
        Write-Host "[*] Clonando $repo..." -ForegroundColor Yellow
        & git clone $Repos[$repo] $dest 2>&1 | Out-Null
    } else {
        Write-Host "[*] Atualizando $repo..." -ForegroundColor Green
        & git -C $dest pull 2>&1 | Out-Null
    }
}

# VALIDAÇÃO ESPECÍFICA: LibreHardwareMonitor é o scanner primordial da
# Phoenix no Windows - se o clone falhou (rede, repo indisponível, etc.),
# isso é fatal, não um warning qualquer perdido no meio dos outros 44 repos.
if ($IsWindows) {
    $lhmDest = Join-Path ".\repos" "LibreHardwareMonitor"
    if (-not (Test-Path $lhmDest) -or -not (Get-ChildItem $lhmDest -ErrorAction SilentlyContinue)) {
        return (& $failContract "Clone do LibreHardwareMonitor falhou ou ficou vazio - scanner de hardware primordial indisponivel." "PX018")
    }
    Write-Host "[OK] LibreHardwareMonitor clonado e validado." -ForegroundColor Green
}


# 4.4. GARANTIA FORÇADA DO TOOLCHAIN DE COMPILAÇÃO (CMake + Compilador C++/Vulkan)
Write-Host "`n=== VERIFICANDO TOOLCHAIN DE COMPILAÇÃO (CMake + C++) ===" -ForegroundColor Cyan

function Update-SessionPath {
    if ($IsWindows) {
        $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        $userPath    = [System.Environment]::GetEnvironmentVariable("Path", "User")
        $env:Path = "$machinePath;$userPath"
    }
}

function Add-ToSessionPath {
    param([string]$Dir)
    if ([string]::IsNullOrWhiteSpace($Dir)) { return $false }
    if (-not (Test-Path $Dir)) { return $false }
    $normalized = $Dir.TrimEnd('\', '/')
    $sep = if ($IsWindows) { ';' } else { ':' }
    $current = $env:Path -split [regex]::Escape($sep)
    if ($current -notcontains $normalized) {
        $env:Path = "$env:Path$sep$normalized"
        Write-Host "[*] PATH forçado com: $normalized" -ForegroundColor DarkGray
        return $true
    }
    return $false
}

function Get-VSBuildToolsPath {
    $vswhereExe = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhereExe) {
        return (& $vswhereExe -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath -latest 2>$null)
    }
    return $null
}

function Get-VSGeneratorName {
    param([string]$VsInstallPath)
    $vswhereExe = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    $catalogVersion = $null
    if ((Test-Path $vswhereExe) -and $VsInstallPath) {
        try {
            $catalogVersion = (& $vswhereExe -products * -path $VsInstallPath -property catalog_productLineVersion 2>$null)
        } catch { $catalogVersion = $null }
    }

    if (-not $catalogVersion -and (Test-Path $vswhereExe) -and $VsInstallPath) {
        try {
            $verString = (& $vswhereExe -products * -path $VsInstallPath -property installationVersion 2>$null)
            if ($verString) {
                $major = [int]($verString.Split('.')[0])
                $catalogVersion = switch ($major) {
                    { $_ -ge 18 } { "2026" }
                    17            { "2022" }
                    16            { "2019" }
                    15            { "2017" }
                    default       { $null }
                }
            }
        } catch { $catalogVersion = $null }
    }

    $generatorMap = @{
        "2026" = "Visual Studio 18 2026"
        "2022" = "Visual Studio 17 2022"
        "2019" = "Visual Studio 16 2019"
        "2017" = "Visual Studio 15 2017"
    }

    if ($catalogVersion -and $generatorMap.ContainsKey([string]$catalogVersion)) {
        return $generatorMap[[string]$catalogVersion]
    }

    Write-Host "[!] Nao foi possivel detectar a versao exata do VS instalado. Assumindo 'Visual Studio 17 2022'." -ForegroundColor DarkYellow
    return "Visual Studio 17 2022"
}

function Find-CMakeOnDisk {
    $candidates = @(
        "C:\Program Files\CMake\bin\cmake.exe",
        "C:\Program Files (x86)\CMake\bin\cmake.exe"
    )
    $vsPath = Get-VSBuildToolsPath
    if ($vsPath) {
        $candidates += (Join-Path $vsPath "Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe")
    }
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    try {
        $found = Get-ChildItem -Path "C:\Program Files","C:\Program Files (x86)" -Filter "cmake.exe" -Recurse -ErrorAction SilentlyContinue -Depth 6 | Select-Object -First 1
        if ($found) { return $found.FullName }
    } catch {}
    return $null
}

 $vsGenerator = $null
 $vsToolsAvailable = $false

function Update-SessionEnvVar {
    param([string]$Name)
    if (-not $IsWindows) { return }
    $machineVal = [System.Environment]::GetEnvironmentVariable($Name, "Machine")
    $userVal    = [System.Environment]::GetEnvironmentVariable($Name, "User")
    $resolved = if ($userVal) { $userVal } elseif ($machineVal) { $machineVal } else { $null }
    if ($resolved) {
        Set-Item -Path "Env:$Name" -Value $resolved
    }
}

function Find-VulkanSDKOnDisk {
    $roots = @("C:\VulkanSDK", "${env:ProgramFiles}\VulkanSDK", "${env:ProgramFiles(x86)}\VulkanSDK")
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        $versionDirs = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
        foreach ($v in $versionDirs) {
            $glslc = Join-Path $v.FullName "Bin\glslc.exe"
            if (Test-Path $glslc) { return $v.FullName }
        }
    }
    return $null
}

function Install-VSBuildTools {
    param([switch]$Force)
    $overrideArgs = "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --includeRecommended"
    if ($Force) {
        & winget install --id Microsoft.VisualStudio.2022.BuildTools --silent --force --accept-package-agreements --accept-source-agreements `
            --override $overrideArgs 2>&1 | Out-Host
    } else {
        & winget install --id Microsoft.VisualStudio.2022.BuildTools --silent --accept-package-agreements --accept-source-agreements `
            --override $overrideArgs 2>&1 | Out-Host
    }
    return $LASTEXITCODE
}

if ($IsWindows) {
    Update-SessionPath
    $vsPath = Get-VSBuildToolsPath

    if (-not $vsPath) {
        Write-Host "[!] Visual Studio Build Tools (C++) não encontrado. Instalando via Winget (forçado)..." -ForegroundColor Yellow
        $installExitCode = Install-VSBuildTools
        Update-SessionPath
        $vsPath = Get-VSBuildToolsPath

        if (-not $vsPath) {
            Write-Host "[!] Winget retornou código $installExitCode. Tentando novamente com --force..." -ForegroundColor Yellow
            $installExitCode = Install-VSBuildTools -Force
            Update-SessionPath
            $vsPath = Get-VSBuildToolsPath
        }

        if ($vsPath) {
            Write-Host "[OK] Visual Studio Build Tools instalado em: $vsPath" -ForegroundColor Green
        } else {
            Write-Host "[X] Instalação do VS Build Tools falhou. O workload C++ NÃO está disponível." -ForegroundColor Red
        }
    } else {
        Write-Host "[OK] Visual Studio Build Tools (C++) encontrado em: $vsPath" -ForegroundColor Green
    }

    $vsToolsAvailable = [bool]$vsPath

    if ($vsPath) {
        $msbuildDir = Join-Path $vsPath "MSBuild\Current\Bin"
        Add-ToSessionPath -Dir $msbuildDir | Out-Null
    }

    $vsGenerator = Get-VSGeneratorName -VsInstallPath $vsPath
    Write-Host "[i] Generator CMake selecionado: $vsGenerator" -ForegroundColor Cyan

    $cmakeCmd = Get-Command cmake -ErrorAction SilentlyContinue
    if (-not $cmakeCmd) {
        Write-Host "[!] CMake não encontrado no PATH. Instalando via Winget..." -ForegroundColor Yellow
        & winget install --id Kitware.CMake --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Host
        Update-SessionPath
    }

    $cmakeCmd = Get-Command cmake -ErrorAction SilentlyContinue
    if (-not $cmakeCmd) {
        $cmakeOnDisk = Find-CMakeOnDisk
        if ($cmakeOnDisk) {
            Add-ToSessionPath -Dir (Split-Path $cmakeOnDisk -Parent) | Out-Null
        }
    } else {
        Add-ToSessionPath -Dir (Split-Path $cmakeCmd.Source -Parent) | Out-Null
    }

    if (Get-Command cmake -ErrorAction SilentlyContinue) {
        Write-Host "[OK] CMake disponível em: $((Get-Command cmake).Source)" -ForegroundColor Green
    } else {
        Write-Host "[X] CMake ainda indisponível após tentativa de instalação e PATH forçado." -ForegroundColor Red
    }

    Write-Host "`n=== VERIFICANDO VULKAN SDK (VULKAN_SDK + glslc) ===" -ForegroundColor Cyan

    Update-SessionEnvVar -Name "VULKAN_SDK"

    if (-not $env:VULKAN_SDK) {
        $vulkanOnDisk = Find-VulkanSDKOnDisk
        if ($vulkanOnDisk) {
            Write-Host "[*] VULKAN_SDK nao estava na sessao, mas o SDK foi encontrado em disco: $vulkanOnDisk" -ForegroundColor Yellow
            $env:VULKAN_SDK = $vulkanOnDisk
        }
    }

    if (-not $env:VULKAN_SDK) {
        Write-Host "[!] Vulkan SDK não encontrado. Instalando via Winget..." -ForegroundColor Yellow
        & winget install --id KhronosGroup.VulkanSDK --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Host
        Update-SessionEnvVar -Name "VULKAN_SDK"
        if (-not $env:VULKAN_SDK) {
            $vulkanOnDisk = Find-VulkanSDKOnDisk
            if ($vulkanOnDisk) { $env:VULKAN_SDK = $vulkanOnDisk }
        }
    }

    if ($env:VULKAN_SDK) {
        $vulkanBin = Join-Path $env:VULKAN_SDK "Bin"
        Add-ToSessionPath -Dir $vulkanBin | Out-Null

        if (Get-Command glslc -ErrorAction SilentlyContinue) {
            Write-Host "[OK] Vulkan SDK disponível em: $env:VULKAN_SDK (glslc: $((Get-Command glslc).Source))" -ForegroundColor Green
        } else {
            Write-Host "[!] VULKAN_SDK setado mas glslc.exe não foi encontrado. Instalação pode estar incompleta." -ForegroundColor Red
        }
    } else {
        Write-Host "[X] Vulkan SDK indisponível. O build com GGML_VULKAN=ON vai falhar." -ForegroundColor Red
    }

} elseif ($IsLinux) {
    # CORREÇÃO ARQUITETURAL: "git" removido daqui - Git agora é garantido só
    # pelo install_phoenix.ps1 (bootstrap), não é mais checado/instalado em
    # três lugares diferentes (bootstrap + linux.ps1 + aqui).
    $requiredPkgs = @("build-essential", "cmake", "pkg-config", "ninja-build", "libvulkan-dev", "vulkan-tools", "glslang-tools", "spirv-tools")
    $missingPkgs = @()
    foreach ($pkg in $requiredPkgs) {
        & dpkg -s $pkg *> $null
        if ($LASTEXITCODE -ne 0) { $missingPkgs += $pkg }
    }

    if ($missingPkgs.Count -gt 0) {
        Write-Host "[!] Pacotes ausentes: $($missingPkgs -join ', '). Instalando via apt..." -ForegroundColor Yellow
        $aptPrefix = if (Get-Command sudo -ErrorAction SilentlyContinue) { "sudo" } else { "" }
        if ($aptPrefix) {
            & sudo apt-get update -y 2>&1 | Out-Host
            & sudo apt-get install -y $missingPkgs 2>&1 | Out-Host
        } else {
            & apt-get update -y 2>&1 | Out-Host
            & apt-get install -y $missingPkgs 2>&1 | Out-Host
        }
    } else {
        Write-Host "[OK] Toolchain completa já presente." -ForegroundColor Green
    }

    if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
        $linuxCmakeCandidates = @("/usr/bin/cmake", "/usr/local/bin/cmake", "/opt/cmake/bin/cmake", "/snap/bin/cmake")
        foreach ($c in $linuxCmakeCandidates) {
            if (Test-Path $c) { Add-ToSessionPath -Dir (Split-Path $c -Parent) | Out-Null; break }
        }
    } else {
        Add-ToSessionPath -Dir (Split-Path (Get-Command cmake).Source -Parent) | Out-Null
    }

    if (Get-Command cmake -ErrorAction SilentlyContinue) {
        Write-Host "[OK] CMake disponível em: $((Get-Command cmake).Source)" -ForegroundColor Green
    } else {
        Write-Host "[X] CMake ainda indisponível." -ForegroundColor Red
    }
}

# 4.5. COMPILAÇÃO DO LLAMA.CPP COM VULKAN NATIVO
Write-Host "`n=== COMPILANDO LLAMA.CPP (Backend Vulkan para CPU/GPU) ===" -ForegroundColor Cyan
 $llamaDir = Join-Path $PhoenixRoot "repos\llama.cpp"
 $llamaCppBuildOk = $false
if (Test-Path $llamaDir) {
    Push-Location $llamaDir
    try {
        $cmakeAvailable = [bool](Get-Command cmake -ErrorAction SilentlyContinue)
        if (-not $cmakeAvailable) {
            Write-Host "[!] CMake indisponível. A Phoenix vai continuar usando o Ollama (CPU)." -ForegroundColor Yellow
        } elseif ($IsWindows -and -not $vsToolsAvailable) {
            Write-Host "[!] Nenhuma instância de Visual Studio com workload C++ foi confirmada. Pulando build." -ForegroundColor Yellow
        } else {
            Write-Host "[*] Configurando build com CMake (Vulkan enabled)..."
            $configureOk = $false
            $buildOk = $false

            if ($IsWindows) {
                if (-not $vsGenerator) { $vsGenerator = "Visual Studio 17 2022" }
                Write-Host "[*] Usando generator: $vsGenerator" -ForegroundColor DarkGray
                & cmake -B build -G $vsGenerator -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON 2>&1 | Out-Host
                $configureOk = ($LASTEXITCODE -eq 0)
                if ($configureOk) {
                    Write-Host "[*] Compilando llama.cpp no Windows..."
                    & cmake --build build --config Release 2>&1 | Out-Host
                    $buildOk = ($LASTEXITCODE -eq 0)
                }
            } else {
                & cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON 2>&1 | Out-Host
                $configureOk = ($LASTEXITCODE -eq 0)
                if ($configureOk) {
                    $cores = (nproc)
                    Write-Host "[*] Compilando llama.cpp no Linux com $cores núcleos..."
                    & cmake --build build --config Release -j $cores 2>&1 | Out-Host
                    $buildOk = ($LASTEXITCODE -eq 0)
                }
            }

            if ($configureOk -and $buildOk) {
                # Confirma com o binário de verdade em disco, não só o
                # exit code do cmake - sinal mais forte de "funciona".
                $llamaServerBin = if ($IsWindows) {
                    Join-Path $llamaDir "build\bin\Release\llama-server.exe"
                } else {
                    Join-Path $llamaDir "build/bin/llama-server"
                }
                if (Test-Path $llamaServerBin) {
                    Write-Host "[OK] llama.cpp compilado com Vulkan nativo! Binario: $llamaServerBin" -ForegroundColor Green
                    $llamaCppBuildOk = $true
                } else {
                    Write-Host "[!] cmake reportou sucesso mas o binario llama-server nao foi encontrado em $llamaServerBin. A Phoenix vai continuar usando o Ollama (CPU)." -ForegroundColor Yellow
                }
            } elseif (-not $configureOk) {
                Write-Host "[!] Falha ao configurar o CMake. A Phoenix vai continuar usando o Ollama (CPU)." -ForegroundColor Yellow
            } else {
                Write-Host "[!] Falha ao compilar llama.cpp. A Phoenix vai continuar usando o Ollama (CPU)." -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "[!] Aviso: Falha ao compilar llama.cpp. A Phoenix vai continuar usando o Ollama. Erro: $($_.Exception.Message)" -ForegroundColor Yellow
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[!] Repositório llama.cpp não encontrado. Pulando compilação." -ForegroundColor DarkYellow
}

# 5. Containers Docker (Ollama + Open WebUI Backup)
Write-Host "`n=== PROVISIONAMENTO DE CONTAINERS ===" -ForegroundColor Cyan

Write-Host "[*] Provisionando Ollama (com CORS liberado)..."
& docker volume create ollama 2>&1 | Out-Null
& docker rm -f ollama 2>&1 | Out-Null
& docker run -d --name ollama --restart unless-stopped -p 11434:11434 -e OLLAMA_ORIGINS="*" -v ollama:/root/.ollama ollama/ollama 2>&1 | Out-Null
Write-Host "[OK] Container Ollama no ar (Porta 11434)." -ForegroundColor Green

# CORREÇÃO: antes isso baixava o qwen3:8b pro Ollama SEMPRE, incondicional,
# mesmo quando o llama.cpp acabou de compilar com sucesso - deixando os
# dois motores "prontos" ao mesmo tempo, e quem decidia qual usar em tempo
# de execução era uma corrida (o mesmo tipo de bug que já resolvemos na
# Aviary). Agora só baixa modelo pro Ollama se o llama.cpp genuinamente
# falhou - Ollama continua disponível como container (Open WebUI depende
# dele), só não fica com um modelo pronto pra disputar a inicialização.
if (-not $llamaCppBuildOk) {
    Write-Host "[*] llama.cpp indisponivel - baixando modelo qwen3:8b para o Ollama (fallback)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    & docker exec ollama ollama pull qwen3:8b 2>&1 | Out-Null
    Write-Host "[OK] Modelo qwen3:8b baixado no Ollama (motor ativo: Ollama)." -ForegroundColor Green
} else {
    Write-Host "[i] llama.cpp compilado com sucesso - Ollama fica disponivel mas sem modelo pre-baixado (motor ativo: llama.cpp)." -ForegroundColor Cyan
}

# Escreve a decisão em disco - o kernel.py le isso em vez de adivinhar
# por corrida de conexão qual motor está "pronto" primeiro.
try {
    $enginePrefPath = Join-Path (Join-Path $PhoenixRoot "data") "engine_preference.json"
    $enginePrefDir = Split-Path $enginePrefPath -Parent
    if (-not (Test-Path $enginePrefDir)) { New-Item -ItemType Directory -Force -Path $enginePrefDir | Out-Null }
    @{
        preferred_llm_engine = if ($llamaCppBuildOk) { "llama.cpp" } else { "ollama" }
        llama_cpp_build_ok = $llamaCppBuildOk
        generated_at = (Get-Date -Format "o")
    } | ConvertTo-Json | Set-Content -Path $enginePrefPath -Encoding UTF8
    Write-Host "[OK] Preferencia de motor gravada em: $enginePrefPath" -ForegroundColor Green
} catch {
    Write-Host "[!] Nao foi possivel gravar data/engine_preference.json: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "[*] Provisionando Open WebUI (Backup na 8010)..."
& docker volume create open-webui 2>&1 | Out-Null
& docker rm -f open_webui 2>&1 | Out-Null
& docker run -d --name open_webui --restart unless-stopped -p 8010:8080 --add-host=host.docker.internal:host-gateway -e OLLAMA_BASE_URL=http://host.docker.internal:11434 -v open-webui:/app/backend/data ghcr.io/open-webui/open-webui:main 2>&1 | Out-Null
Write-Host "[OK] Container Open WebUI no ar (http://localhost:8010)." -ForegroundColor Green

# 6. Instalação e Inicialização do Phoenix Studio (Node.js na Porta 3000)
Write-Host "`n=== INICIANDO PHOENIX STUDIO (NODE.JS) ===" -ForegroundColor Cyan
 $studioDir = Join-Path $PhoenixRoot "repos\phoenix_studio"
if (-not (Test-Path $studioDir)) {
    $studioDir = Join-Path $PhoenixRoot "platform_source"
}

if (Test-Path $studioDir) {
    Push-Location $studioDir
    if (Test-Path "package.json") {
        Write-Host "[*] Instalando dependencias NPM do Phoenix Studio..." -ForegroundColor Yellow
        & npm install 2>&1 | Out-Host
        
        Write-Host "[*] Iniciando Phoenix Studio na porta 3000..." -ForegroundColor Yellow
        
        if ($IsWindows) {
            Start-Process -FilePath "npm" -ArgumentList "run dev" -WindowStyle Hidden
        } else {
            $logOut = Join-Path $PhoenixRoot "logs/phoenix_studio_out.log"
            $logErr = Join-Path $PhoenixRoot "logs/phoenix_studio_err.log"
            Start-Process -FilePath "npm" -ArgumentList "run dev" -RedirectStandardOutput $logOut -RedirectStandardError $logErr -NoNewWindow
        }
        
        Write-Host "[OK] Phoenix Studio no ar (http://localhost:3000)." -ForegroundColor Green
    } else {
        Write-Host "[!] package.json nao encontrado em $studioDir" -ForegroundColor DarkYellow
    }
    Pop-Location
} else {
    Write-Host "[!] Repositorio do Phoenix Studio nao encontrado." -ForegroundColor DarkYellow
}

# 7. Instalação e Configuração do SearXNG (Busca na Web)
Write-Host "`n=== CONFIGURANDO STACK SEARXNG ===" -ForegroundColor Cyan
 $searxBase = Join-Path $PhoenixRoot "searxng-docker"
docker stop searxng searxng-phoenix searxng-webui 2>$null | Out-Null
docker rm searxng searxng-phoenix searxng-webui 2>$null | Out-Null
Remove-Item -Recurse -Force $searxBase -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $searxBase | Out-Null

# PHX-FIX: SearXNG WebUI movida para 8088 para liberar a 8081 pro Llama.cpp
Set-Content -Path (Join-Path $searxBase "docker-compose.yml") -Encoding UTF8 -Value @"
services:
  searxng-phoenix:
    container_name: searxng-phoenix
    image: searxng/searxng:latest
    ports: ["8080:8080"]
    volumes: ["./searxng-phoenix:/etc/searxng:rw"]
    environment:
      - SEARXNG_HOSTNAME=localhost:8080/
      - SEARXNG_BIND_ADDRESS=0.0.0.0
      - FORCE_OWNERSHIP=true
    restart: unless-stopped
  searxng-webui:
    container_name: searxng-webui
    image: searxng/searxng:latest
    ports: ["8088:8080"]
    volumes: ["./searxng-webui:/etc/searxng:rw"]
    environment:
      - SEARXNG_HOSTNAME=localhost:8088/
      - SEARXNG_BIND_ADDRESS=0.0.0.0
      - FORCE_OWNERSHIP=true
    restart: unless-stopped
"@

Push-Location $searxBase
Write-Host "[SearXNG] Subindo containers..." -ForegroundColor Yellow
 $composeUpOutput = docker compose up -d 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[SearXNG] ERRO: 'docker compose up -d' falhou." -ForegroundColor Red
    $composeUpOutput | Out-Host
    Pop-Location
    return (& $failContract "docker compose up -d falhou." "PX016")
}

 $maxWaitSeconds = 180
 $elapsed = 0
 $filesReady = $false
 $readyCheckPy = @'
import sys
p = "/etc/searxng/settings.yml"
try:
    with open(p, "r", encoding="utf-8") as f: c = f.read()
except Exception: print("NOTFOUND"); sys.exit(1)
if "server:" in c.strip() and "secret_key:" in c.strip(): print("READY"); sys.exit(0)
print("INCOMPLETE"); sys.exit(1)
'@
 $readyCheckB64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($readyCheckPy))

function Test-SettingsInsideContainer {
    param([string]$containerName, [string]$scriptB64)
    try { $out = docker exec $containerName sh -c "echo $scriptB64 | base64 -d | python3 -" 2>&1; return ($out -match "READY") } catch { return $false }
}

while ($elapsed -lt $maxWaitSeconds) {
    if ((Test-SettingsInsideContainer "searxng-phoenix" $readyCheckB64) -and (Test-SettingsInsideContainer "searxng-webui" $readyCheckB64)) { $filesReady = $true; break }
    Start-Sleep -Seconds 3
    $elapsed += 3
}

if (-not $filesReady) {
    Write-Host "[SearXNG] ERRO: settings.yml nao foi gerado." -ForegroundColor Red
    docker compose down 2>&1 | Out-Null
    Pop-Location
    return (& $failContract "SearXNG falhou." "PX014")
}

 $pyPatchScript = @'
import re, sys
path = "/etc/searxng/settings.yml"
with open(path, "r", encoding="utf-8") as f: content = f.read()
if "search:" not in content: content += "\nsearch:\n  formats:\n    - html\n    - json\n"
elif "formats:" not in content: content = re.sub(r"(search:\s*\n)", r"\1  formats:\n    - html\n    - json\n", content, count=1)
if "limiter:" not in content: content = re.sub(r"(server:\s*\n)", r"\1  limiter: false\n", content, count=1)
else: content = re.sub(r"limiter:\s*(true|True)", "limiter: false", content)
with open(path, "w", encoding="utf-8") as f: f.write(content)
print("PATCH_OK")
'@
 $pyPatchB64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($pyPatchScript))
docker exec searxng-phoenix sh -c "echo $pyPatchB64 | base64 -d | python3 -" 2>&1 | Out-Null
docker exec searxng-webui sh -c "echo $pyPatchB64 | base64 -d | python3 -" 2>&1 | Out-Null
docker restart searxng-phoenix searxng-webui 2>&1 | Out-Null
Start-Sleep -Seconds 10
Pop-Location

 $test1 = curl -s "http://localhost:8080/search?q=teste&format=json"
 $test2 = curl -s -X POST "http://localhost:8088/search?q=teste&format=json"
if ($test1 -notmatch '"results"' -or $test2 -notmatch '"results"') {
    return (& $failContract "SearXNG search test failed." "PX015")
}
Write-Host "[OK] SearXNG Stack validada (8080 API / 8088 WebUI)." -ForegroundColor Green

# 8. Inicializacao da Phoenix
Write-Host "`n=== INICIANDO PHOENIX ENGINE ===" -ForegroundColor Green
 $pythonExe = $null
if ($IsWindows) {
    $pythonExe = ".\.venv\Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) { $pythonExe = "C:\Program Files\Python312\python.exe" }
} else {
    $pythonExe = ".\.venv/bin/python"
    if (-not (Test-Path $pythonExe)) { $pythonExe = "python3" }
}

if (-not (Test-Path $pythonExe)) { return (& $failContract "Interpretador Python nao encontrado." "PX011") }
 $proc = Start-Process $pythonExe -ArgumentList "api_server.py" -PassThru -NoNewWindow

 $apiReady = $false
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 2
    if ($proc.HasExited) { return (& $failContract "api_server encerrou prematuramente." "PX012") }
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 2
        if ($response.status -eq "healthy") { $apiReady = $true; break }
    } catch {}
}

if ($apiReady) {
    return @{ Name="Common"; Version="5.0.0"; Success=$true; ErrorCode=""; Warnings=@(); Errors=@(); RestartRequired=$false; Artifacts=@("api_server", "searxng-phoenix", "searxng-webui", "phoenix_studio", "open_webui"); Timestamp=Get-Date }
} else {
    return (& $failContract "API nao respondeu ao health check." "PX013")
}