# install/common.ps1
# =====================================================================
# PHOENIX COMMON 7.1 — Enterprise Bootstrap (Windows + Multi-distro Linux)
# =====================================================================

 $env:PHOENIX_LLM_DEVICE   = "CPU"
 $env:PHOENIX_IMAGE_DEVICE = "GPU"
 $env:PHOENIX_LLM_NGL      = "0"

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

 $PhoenixWorkspace   = $null
 $PhoenixStorageData = $null
 $_storagePath = Join-Path $env:ProgramData "Phoenix\storage.json"
if (Test-Path $_storagePath) {
    try {
        $PhoenixStorageData = Get-Content $_storagePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $PhoenixWorkspace   = $PhoenixStorageData.workspace
        if ($PhoenixWorkspace) {
            Write-Host "[OK] storage.json lido: workspace = $PhoenixWorkspace" -ForegroundColor Green
        }
    } catch {
        Write-Host "[!] Falha ao ler storage.json: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

 $failContract = {
    param([string]$errMsg, [string]$code)
    return @{ Name="Common"; Version="N/A"; Success=$false; ErrorCode=$code; Warnings=@(); Errors=@($errMsg); RestartRequired=$false; Artifacts=@(); Timestamp=Get-Date }
}

function Update-SessionPath {
    if ($IsWindows) {
        $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        $userPath    = [System.Environment]::GetEnvironmentVariable("Path", "User")
        $env:Path = "$machinePath;$userPath"
    } elseif ($IsLinux) {
        $candidatePaths = @("/usr/local/bin", "/usr/local/sbin", "/usr/bin", "/usr/sbin", "/bin", "/sbin", "$HOME/.local/bin")
        $sep = ':'
        $current = $env:Path -split [regex]::Escape($sep)
        foreach ($p in $candidatePaths) {
            if ((Test-Path $p) -and ($current -notcontains $p)) {
                $env:Path = "$env:Path$sep$p"
                $current = $env:Path -split [regex]::Escape($sep)
            }
        }
    }
}

function Add-ToSessionPath {
    param([string]$Dir)
    if ([string]::IsNullOrWhiteSpace($Dir) -or -not (Test-Path $Dir)) { return $false }
    $normalized = $Dir.TrimEnd('\', '/')
    $sep = if ($IsWindows) { ';' } else { ':' }
    $current = $env:Path -split [regex]::Escape($sep)
    if ($current -notcontains $normalized) {
        $env:Path = "$env:Path$sep$normalized"
        return $true
    }
    return $false
}

function Resolve-PhoenixGit {
    Write-Host "`n=== RESOLUÇÃO DO GIT ===" -ForegroundColor Cyan
    if (Get-Command git -ErrorAction SilentlyContinue) { return $true }
    Write-Host "[!] Git não encontrado. Instalando..." -ForegroundColor Yellow
    if ($IsWindows) {
        & winget install --id Git.Git -e --source winget --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Host
        Update-SessionPath
        if (Get-Command git -ErrorAction SilentlyContinue) { return $true }
    }
    return $false
}

function Get-LatestWingetPythonId {
    try {
        $raw = & winget search --id "Python.Python.3." --source winget 2>&1
        $ids = [regex]::Matches(($raw -join "`n"), "Python\.Python\.3\.\d+") | ForEach-Object { $_.Value } | Select-Object -Unique
        if (-not $ids -or $ids.Count -eq 0) { return $null }
        return $ids | Sort-Object { [int]($_ -replace 'Python\.Python\.3\.', '') } -Descending | Select-Object -First 1
    } catch { return $null }
}

function Resolve-PhoenixPython {
    Write-Host "`n=== RESOLUÇÃO DO PYTHON ===" -ForegroundColor Cyan
    if ($IsWindows) {
        Update-SessionPath
        $pythonInPath = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonInPath) { return $pythonInPath.Source }
        
        Write-Host "[!] Python não encontrado no PATH. Instalando..." -ForegroundColor Yellow
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            $latestId = Get-LatestWingetPythonId
            if ($latestId) {
                & winget install -e --id $latestId --scope machine --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Host
            } else {
                & winget install -e --id "Python.Python.3" --scope machine --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Host
            }
            Update-SessionPath
            $pythonInPath = Get-Command python -ErrorAction SilentlyContinue
            if ($pythonInPath) { return $pythonInPath.Source }
        }
        return $null
    }
    if ($IsLinux) {
        $linuxPython = Get-Command python3 -ErrorAction SilentlyContinue
        if ($linuxPython) { return $linuxPython.Source }
        Write-Host "[!] python3 não encontrado. Instalando..." -ForegroundColor Yellow
        $sudo = if (Get-Command sudo -ErrorAction SilentlyContinue) { "sudo" } else { "" }
        if (Get-Command apt-get -ErrorAction SilentlyContinue) {
            $pkgs = @("python3", "python3-pip", "python3-venv", "python3-dev")
            if ($sudo) { & sudo apt-get update -y 2>&1 | Out-Host; & sudo apt-get install -y @pkgs 2>&1 | Out-Host } else { & apt-get update -y 2>&1 | Out-Host; & apt-get install -y @pkgs 2>&1 | Out-Host }
        }
        Update-SessionPath
        return (Get-Command python3 -ErrorAction SilentlyContinue).Source
    }
    return $null
}

function Test-PhoenixPythonBinary {
    param([string]$PythonExe)
    if (-not $PythonExe) { return $false }
    try {
        $versionOutput = & $PythonExe --version 2>&1
        if ($LASTEXITCODE -ne 0) { return $false }
        return $true
    } catch { return $false }
}

function Test-PhoenixVenvModule {
    param([string]$PythonExe)
    try {
        & $PythonExe -c "import venv" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { return $true }
    } catch {}
    if ($IsLinux) {
        $sudo = if (Get-Command sudo -ErrorAction SilentlyContinue) { "sudo" } else { "" }
        if (Get-Command apt-get -ErrorAction SilentlyContinue) {
            if ($sudo) { & sudo apt-get install -y python3-venv 2>&1 | Out-Host } else { & apt-get install -y python3-venv 2>&1 | Out-Host }
        }
    }
    try {
        & $PythonExe -c "import venv" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { return $true }
    } catch {}
    return $false
}

if (-not (Resolve-PhoenixGit)) { return (& $failContract "Git não foi encontrado e não pode ser instalado." "PX020") }
if (-not (Test-Path ".\api_server.py")) { return (& $failContract "api_server.py nao encontrado" "PX010") }

# PHX-FIX: Limpeza automática do ChromaDB para resolver mismatch de dimensões (768 vs 384)
 $_chromaDbPath = Join-Path $PhoenixRoot "data\chroma_db"
if (Test-Path $_chromaDbPath) {
    Write-Host "[*] Limpando cache do ChromaDB (mismatch de dimensões)..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $_chromaDbPath -ErrorAction SilentlyContinue
}

 $VenvDir      = ".venv"
 $VenvActivate = if ($IsWindows) { Join-Path $VenvDir "Scripts\Activate.ps1" } else { Join-Path $VenvDir "bin/Activate.ps1" }
 $VenvPython   = if ($IsWindows) { Join-Path $VenvDir "Scripts\python.exe" } else { Join-Path $VenvDir "bin/python" }

if ((Test-Path $VenvActivate) -and -not (Test-PhoenixPythonBinary -PythonExe $VenvPython)) {
    Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue
}

if (-not (Test-Path $VenvActivate)) {
    $pythonExeToUse = Resolve-PhoenixPython
    if (-not $pythonExeToUse) { return (& $failContract "Python não encontrado." "PX019") }
    if (-not (Test-PhoenixPythonBinary -PythonExe $pythonExeToUse)) { return (& $failContract "Interpretador corrompido." "PX023") }
    if (-not (Test-PhoenixVenvModule -PythonExe $pythonExeToUse)) { return (& $failContract "Módulo venv indisponível." "PX022") }
    & $pythonExeToUse -m venv $VenvDir 2>&1 | Out-Host
    if (-not (Test-Path $VenvActivate)) { return (& $failContract "Falha ao criar venv." "PX021") }
}
. $VenvActivate

Write-Host "`n=== DEPENDÊNCIAS PYTHON COMUNS ===" -ForegroundColor Cyan
& python -m pip install --upgrade pip 2>&1 | Out-Host
# PHX-NEW: pymupdf/pymupdf4llm (PDF), python-docx (DOCX), openpyxl (XLSX)
# e python-pptx (PPTX) - cobrem os 4 formatos que a Document Engine lê e
# edita (ver phoenix_kernel/documents/engine.py). Tudo puro Python, sem
# container Docker novo.
& python -m pip install fastapi uvicorn psutil chromadb astor httpx google-cloud-firestore python-multipart pymupdf pymupdf4llm python-docx openpyxl python-pptx 2>&1 | Out-Host
if ($IsWindows) {
    & python -m pip install pythonnet HardwareMonitor wmi pywin32 2>&1 | Out-Host
}

Write-Host "`n=== CLONANDO REPOSITORIOS BASE (AVIARY) ===" -ForegroundColor Cyan
 $env:GIT_TERMINAL_PROMPT = "0"
if (-not (Test-Path ".\repos")) { New-Item -ItemType Directory -Force -Path ".\repos" | Out-Null }
 $Repos = @{
    "llama.cpp" = "https://github.com/ggml-org/llama.cpp"
    "phoenix_studio" = "https://github.com/aivisionslab-studios/phoenix-engine.git"
    "ComfyUI" = "https://github.com/comfyanonymous/ComfyUI"
    "stable-diffusion-webui" = "https://github.com/AUTOMATIC1111/stable-diffusion-webui"
    "stable-diffusion-webui-forge" = "https://github.com/lllyasviel/stable-diffusion-webui-forge"
    "stable-diffusion.cpp" = "https://github.com/leejet/stable-diffusion.cpp"
    "InvokeAI" = "https://github.com/invoke-ai/InvokeAI"
    "SwarmUI" = "https://github.com/mcmonkeyprojects/SwarmUI"
    "open-interpreter" = "https://github.com/OpenInterpreter/open-interpreter"
    "OpenHands" = "https://github.com/All-Hands-AI/OpenHands"
    "OpenDevin" = "https://github.com/OpenDevin/OpenDevin"
    "devika" = "https://github.com/stitionai/devika"
    "bolt.diy" = "https://github.com/stackblitz-labs/bolt.diy"
    "continue" = "https://github.com/continuedev/continue"
    "crewAI" = "https://github.com/crewAIInc/crewAI"
    "autogen" = "https://github.com/microsoft/autogen"
    "semantic-kernel" = "https://github.com/microsoft/semantic-kernel"
    "langgraph" = "https://github.com/langchain-ai/langgraph"
    "openai-agents-python" = "https://github.com/openai/openai-agents-python"
    "OpenWebUI" = "https://github.com/open-webui/open-webui"
    "LibreChat" = "https://github.com/danny-avila/LibreChat"
    "anything-llm" = "https://github.com/Mintplex-Labs/anything-llm"
    "lobe-chat" = "https://github.com/lobehub/lobe-chat"
    "Flowise" = "https://github.com/FlowiseAI/Flowise"
    "big-AGI" = "https://github.com/enricoros/big-AGI"
    "SillyTavern" = "https://github.com/SillyTavern/SillyTavern"
    "chatbox" = "https://github.com/chatboxai/chatbox"
    "gpt4all" = "https://github.com/nomic-ai/gpt4all"
    "cherry-studio" = "https://github.com/CherryHQ/cherry-studio"
    "enchanted" = "https://github.com/AugustDev/enchanted"
    "jan" = "https://github.com/janhq/jan"
    "faster-whisper" = "https://github.com/SYSTRAN/faster-whisper"
    "Piper" = "https://github.com/rhasspy/piper"
    "Coqui-TTS" = "https://github.com/idiap/coqui-ai-TTS"
    "Kokoro" = "https://github.com/hexgrad/kokoro"
    "Applio" = "https://github.com/IAHispano/Applio"
}
if ($IsWindows) { $Repos["LibreHardwareMonitor"] = "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor.git" }

foreach ($repo in $Repos.Keys) {
    $dest = Join-Path ".\repos" $repo
    if (!(Test-Path $dest)) { 
        & git clone $Repos[$repo] $dest 2>&1 | Out-Host
        # PHX-FIX: Inicializar submódulos do stable-diffusion.cpp (necessário para a pasta ggml)
        if ($repo -eq "stable-diffusion.cpp") {
            Push-Location $dest
            & git submodule update --init --recursive 2>&1 | Out-Host
            Pop-Location
        }
    } else { 
        & git -C $dest pull 2>&1 | Out-Null 
        if ($repo -eq "stable-diffusion.cpp") {
            Push-Location $dest
            & git submodule update --init --recursive 2>&1 | Out-Null
            Pop-Location
        }
    }
}

# =====================================================================
# DOWNLOAD DO BINÁRIO PIPER TTS E VOZES NEURAIS (Windows)
# =====================================================================
if ($IsWindows) {
    $piperDir = Join-Path $PhoenixRoot "repos\Piper"
    $piperExe = Join-Path $piperDir "piper.exe"
    $espeakDataDir = Join-Path $piperDir "espeak-ng-data"
    
    # PHX-FIX: Se faltar o exe OU a pasta de fonemas, refaz o download
    if (-not (Test-Path $piperExe) -or -not (Test-Path $espeakDataDir)) {
        Write-Host "`n=== BAIXANDO/ATUALIZANDO BINÁRIO PIPER TTS ===" -ForegroundColor Cyan
        $piperUrl = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
        $piperZip = Join-Path $env:TEMP "piper.zip"
        $tempExtractDir = Join-Path $env:TEMP "piper_extract"
        
        try {
            Invoke-WebRequest -Uri $piperUrl -OutFile $piperZip -UseBasicParsing
            
            # Limpa pasta temporária de extração se existir
            if (Test-Path $tempExtractDir) { Remove-Item -Recurse -Force $tempExtractDir }
            
            # Extrai para a pasta temporária primeiro
            Expand-Archive -Path $piperZip -DestinationPath $tempExtractDir -Force
            
            # Garante que a pasta de destino exista
            if (-not (Test-Path $piperDir)) { New-Item -ItemType Directory -Force -Path $piperDir | Out-Null }
            
            # PHX-FIX (auditoria 2026-08-09, revisado após teste real):
            # O zip oficial contém UMA pasta "piper/" aninhada dentro.
            $tempItems = Get-ChildItem -Path $tempExtractDir -Force
            $tempDirs  = $tempItems | Where-Object { $_.PSIsContainer }
            $tempFiles = $tempItems | Where-Object { -not $_.PSIsContainer }
            if ($tempDirs.Count -eq 1 -and $tempFiles.Count -eq 0) {
                $realSource = $tempDirs[0].FullName
            } else {
                $realSource = $tempExtractDir
            }
            Copy-Item -Path (Join-Path $realSource "*") -Destination $piperDir -Recurse -Force

            # Limpeza
            Remove-Item $piperZip -Force
            Remove-Item $tempExtractDir -Recurse -Force
            
            # PHX-FIX: valida que a subpasta essencial sobreviveu à cópia
            if (Test-Path $espeakDataDir) {
                Write-Host "[OK] Piper TTS binário baixado e extraído para $piperDir (espeak-ng-data OK)." -ForegroundColor Green
            } else {
                Write-Host "[AVISO] Piper extraído, mas 'espeak-ng-data' não foi encontrada em $piperDir. TTS provavelmente vai falhar." -ForegroundColor Yellow
            }
        } catch {
            Write-Host "[X] Falha ao baixar/extrair Piper: $($_.Exception.Message)" -ForegroundColor Red
        }
    }

    # PHX-FIX: Baixar pacote completo de vozes neurais para os idiomas padrão da Aviary
    $workspaceDir = if ($PhoenixWorkspace) { $PhoenixWorkspace } elseif ($env:PHOENIX_WORKSPACE) { $env:PHOENIX_WORKSPACE } else { Join-Path $PhoenixRoot "Workstations" }
    $piperVoiceDir = Join-Path $workspaceDir "Models\Voice\Piper"
    if (-not (Test-Path $piperVoiceDir)) { New-Item -ItemType Directory -Force -Path $piperVoiceDir | Out-Null }

    $voicesToDownload = @(
        @{ Name="pt_BR-faber-medium"; Url="https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx" },
        @{ Name="pt_BR-cadu-medium"; Url="https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/cadu/medium/pt_BR-cadu-medium.onnx" },
        @{ Name="en_US-ryan-medium"; Url="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx" },
        @{ Name="en_US-amy-medium"; Url="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx" },
        @{ Name="en_GB-alan-medium"; Url="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx" },
        @{ Name="es_ES-davefx-medium"; Url="https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx" }
    )

    Write-Host "`n=== BAIXANDO VOZES NEURAIS PIPER ===" -ForegroundColor Cyan
    foreach ($voice in $voicesToDownload) {
        $onnxPath = Join-Path $piperVoiceDir "$($voice.Name).onnx"
        $jsonPath = Join-Path $piperVoiceDir "$($voice.Name).onnx.json"
        
        if (-not (Test-Path $onnxPath)) {
            try {
                Write-Host "[*] Baixando voz $($voice.Name)..."
                Invoke-WebRequest -Uri $voice.Url -OutFile $onnxPath -UseBasicParsing
                Invoke-WebRequest -Uri "$($voice.Url).json" -OutFile $jsonPath -UseBasicParsing
            } catch {
                Write-Host "[X] Falha ao baixar voz $($voice.Name): $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
    Write-Host "[OK] Vozes neurais verificadas." -ForegroundColor Green
}

# =====================================================================
# TOOLCHAIN E COMPILAÇÃO DO LLAMA.CPP
# =====================================================================
Write-Host "`n=== VERIFICANDO TOOLCHAIN DE COMPILACAO (CMake + C++) ===" -ForegroundColor Cyan

 $vsGenerator = $null
 $vsToolsAvailable = $false

function Get-VSBuildToolsPath {
    $vswhereExe = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhereExe) { return (& $vswhereExe -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath -latest 2>$null) }
    return $null
}

function Get-VSGeneratorName {
    param([string]$VsInstallPath)
    $vswhereExe = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    $catalogVersion = $null
    if ((Test-Path $vswhereExe) -and $VsInstallPath) {
        try { $catalogVersion = (& $vswhereExe -products * -path $VsInstallPath -property catalog_productLineVersion 2>$null) } catch {}
    }
    if (-not $catalogVersion -and (Test-Path $vswhereExe) -and $VsInstallPath) {
        try {
            $verString = (& $vswhereExe -products * -path $VsInstallPath -property installationVersion 2>$null)
            if ($verString) {
                $major = [int]($verString.Split('.')[0])
                $catalogVersion = switch ($major) { { $_ -ge 18 } { "2026" } 17 { "2022" } 16 { "2019" } 15 { "2017" } default { $null } }
            }
        } catch {}
    }
    $generatorMap = @{ "2026"="Visual Studio 18 2026"; "2022"="Visual Studio 17 2022"; "2019"="Visual Studio 16 2019"; "2017"="Visual Studio 15 2017" }
    if ($catalogVersion -and $generatorMap.ContainsKey([string]$catalogVersion)) { return $generatorMap[[string]$catalogVersion] }
    return "Visual Studio 17 2022"
}

function Find-CMakeOnDisk {
    $candidates = @("C:\Program Files\CMake\bin\cmake.exe", "C:\Program Files (x86)\CMake\bin\cmake.exe")
    $vsPath = Get-VSBuildToolsPath
    if ($vsPath) { $candidates += (Join-Path $vsPath "Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe") }
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    return $null
}

if ($IsWindows) {
    Update-SessionPath
    $vsPath = Get-VSBuildToolsPath
    if (-not $vsPath) {
        & winget install --id Microsoft.VisualStudio.2022.BuildTools --silent --force --accept-package-agreements --accept-source-agreements --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --includeRecommended" 2>&1 | Out-Host
        Update-SessionPath
        $vsPath = Get-VSBuildToolsPath
    }
    $vsToolsAvailable = [bool]$vsPath
    if ($vsPath) { Add-ToSessionPath -Dir (Join-Path $vsPath "MSBuild\Current\Bin") | Out-Null }
    $vsGenerator = Get-VSGeneratorName -VsInstallPath $vsPath

    if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
        & winget install --id Kitware.CMake --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Host
        Update-SessionPath
    }
    if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
        $cmakeOnDisk = Find-CMakeOnDisk
        if ($cmakeOnDisk) { Add-ToSessionPath -Dir (Split-Path $cmakeOnDisk -Parent) | Out-Null }
    }
    
    if (-not (Get-Command ninja -ErrorAction SilentlyContinue)) {
        & winget install --id Ninja-build.Ninja --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Host
        Update-SessionPath
    }

    Write-Host "`n=== VERIFICANDO VULKAN SDK ===" -ForegroundColor Cyan

    # PHX-FIX: Blindagem contra 'Cannot bind argument to parameter Path because it is null'.
    # Get-ChildItem pode retornar $null (pasta vazia/inexistente) - iterar com foreach
    # em vez de Select-Object -First 1 evita o Join-Path explodir com $v nulo.
    function Find-VulkanSdk {
        $roots = @("C:\VulkanSDK", "${env:ProgramFiles}\VulkanSDK", "${env:ProgramFiles(x86)}\VulkanSDK")
        foreach ($root in $roots) {
            if (-not (Test-Path $root)) { continue }
            $vDirs = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
            foreach ($v in $vDirs) {
                $glslcPath = Join-Path $v.FullName "Bin\glslc.exe"
                if (Test-Path $glslcPath) { return $v.FullName }
            }
        }
        return $null
    }

    if (-not $env:VULKAN_SDK) { $env:VULKAN_SDK = Find-VulkanSdk }

    if (-not $env:VULKAN_SDK) {
        Write-Host "[*] Vulkan SDK nao encontrado. Instalando via winget..." -ForegroundColor Yellow
        & winget install --id KhronosGroup.VulkanSDK --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Host
        Update-SessionPath
        # PHX-FIX: re-escaneia apos o install - sem isso $env:VULKAN_SDK ficava vazio
        # na mesma sessao mesmo com o SDK recem-instalado, e o CMake compilava sem Vulkan.
        $env:VULKAN_SDK = Find-VulkanSdk
    }

    if ($env:VULKAN_SDK) {
        Add-ToSessionPath -Dir (Join-Path $env:VULKAN_SDK "Bin") | Out-Null
        Write-Host "[OK] VULKAN_SDK definido para: $env:VULKAN_SDK" -ForegroundColor Green
    } else {
        Write-Host "[!] AVISO CRITICO: Vulkan SDK nao encontrado. A compilacao do llama.cpp e stable-diffusion.cpp com -DGGML_VULKAN=ON provavelmente falhara." -ForegroundColor Red
    }

} elseif ($IsLinux) {
    $requiredPkgs = @("build-essential", "cmake", "pkg-config", "ninja-build", "libvulkan-dev", "vulkan-tools", "glslang-tools", "spirv-tools")
    $missingPkgs = @()
    foreach ($pkg in $requiredPkgs) { & dpkg -s $pkg *> $null; if ($LASTEXITCODE -ne 0) { $missingPkgs += $pkg } }
    if ($missingPkgs.Count -gt 0) {
        $aptPrefix = if (Get-Command sudo -ErrorAction SilentlyContinue) { "sudo" } else { "" }
        if ($aptPrefix) { & sudo apt-get update -y 2>&1 | Out-Host; & sudo apt-get install -y $missingPkgs 2>&1 | Out-Host } else { & apt-get update -y 2>&1 | Out-Host; & apt-get install -y $missingPkgs 2>&1 | Out-Host }
    }
}

Write-Host "`n=== COMPILANDO LLAMA.CPP (Backend Vulkan para CPU/GPU) ===" -ForegroundColor Cyan
 $llamaDir = Join-Path $PhoenixRoot "repos\llama.cpp"
 $llamaCppBuildOk = $false
 $llamaServerBinResolved = $null

function Get-LlamaServerBinCandidates {
    param([string]$LlamaDir, [bool]$IsWin)
    if ($IsWin) { return @((Join-Path $LlamaDir "build\bin\llama-server.exe"), (Join-Path $LlamaDir "build\bin\Release\llama-server.exe")) }
    else { return @((Join-Path $LlamaDir "build/bin/llama-server")) }
}

if (Test-Path $llamaDir) {
    Push-Location $llamaDir
    try {
        if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
            Write-Host "[!] CMake indisponível." -ForegroundColor Yellow
        } elseif ($IsWindows -and -not $vsToolsAvailable) {
            Write-Host "[!] VS Build Tools indisponível." -ForegroundColor Yellow
        } else {
            $cacheFile = Join-Path $llamaDir "build\CMakeCache.txt"
            if (Test-Path $cacheFile) {
                $cachedHome = (Select-String -Path $cacheFile -Pattern '^CMAKE_HOME_DIRECTORY:INTERNAL=(.*)$' -ErrorAction SilentlyContinue | ForEach-Object { $_.Matches[0].Groups[1].Value } | Select-Object -First 1)
                if ($cachedHome -and ($cachedHome.TrimEnd('/','\') -ne $llamaDir.TrimEnd('/','\'))) {
                    Remove-Item -Recurse -Force (Join-Path $llamaDir "build") -ErrorAction SilentlyContinue
                }
            }

            $configureOk = $false
            $buildOk = $false

            if ($IsWindows) {
                $ninjaAvailable = [bool](Get-Command ninja -ErrorAction SilentlyContinue)
                if ($ninjaAvailable) {
                    Write-Host "[*] Usando generator: Ninja" -ForegroundColor DarkGray
                    
                    $vsDevShell = $null
                    if ($vsPath) {
                        $devShellScripts = @(
                            (Join-Path $vsPath "Common7\Tools\Launch-VsDevShell.ps1"),
                            (Join-Path $vsPath "Common7\Tools\Enter-VsDevShell.ps1")
                        )
                        foreach ($script in $devShellScripts) {
                            if (Test-Path $script) { $vsDevShell = $script; break }
                        }
                    }

                    if ($vsDevShell) {
                        Write-Host "[*] Ativando ambiente MSVC via: $vsDevShell" -ForegroundColor DarkGray
                        & $vsDevShell -SkipAutomaticLocation -Arch amd64
                        
                        $clCheck = Get-Command cl.exe -ErrorAction SilentlyContinue
                        if ($clCheck) {
                            Write-Host "[OK] cl.exe resolvido em: $($clCheck.Source)" -ForegroundColor Green
                            & cmake -B build -G "Ninja" -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON -DCMAKE_CXX_FLAGS="/bigobj" 2>&1 | Out-Host
                            $configureOk = ($LASTEXITCODE -eq 0)
                            if ($configureOk) {
                                Write-Host "[*] Compilando llama.cpp no Windows (Ninja)..."
                                & cmake --build build 2>&1 | Out-Host
                                $buildOk = ($LASTEXITCODE -eq 0)
                            }
                        } else {
                            Write-Host "[!] cl.exe NAO encontrado. Tentando fallback MSBuild..." -ForegroundColor Red
                            & cmake -B build -G $vsGenerator -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON -DCMAKE_CXX_FLAGS="/bigobj" 2>&1 | Out-Host
                            $configureOk = ($LASTEXITCODE -eq 0)
                            if ($configureOk) { & cmake --build build --config Release 2>&1 | Out-Host; $buildOk = ($LASTEXITCODE -eq 0) }
                        }
                    } else {
                        Write-Host "[!] VsDevShell.ps1 não encontrado. Tentando CMake sem ambiente MSVC..." -ForegroundColor Yellow
                        & cmake -B build -G "Ninja" -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON -DCMAKE_CXX_FLAGS="/bigobj" 2>&1 | Out-Host
                        $configureOk = ($LASTEXITCODE -eq 0)
                        if ($configureOk) { & cmake --build build 2>&1 | Out-Host; $buildOk = ($LASTEXITCODE -eq 0) }
                    }
                } else {
                    Write-Host "[!] Ninja não encontrado - usando fallback: $vsGenerator" -ForegroundColor DarkYellow
                    & cmake -B build -G $vsGenerator -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON -DCMAKE_CXX_FLAGS="/bigobj" 2>&1 | Out-Host
                    $configureOk = ($LASTEXITCODE -eq 0)
                    if ($configureOk) { & cmake --build build --config Release 2>&1 | Out-Host; $buildOk = ($LASTEXITCODE -eq 0) }
                }
            } else {
                & cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON 2>&1 | Out-Host
                $configureOk = ($LASTEXITCODE -eq 0)
                if ($configureOk) { $cores = (nproc); & cmake --build build --config Release -j $cores 2>&1 | Out-Host; $buildOk = ($LASTEXITCODE -eq 0) }
            }

            if ($configureOk -and $buildOk) {
                $llamaServerBin = (Get-LlamaServerBinCandidates -LlamaDir $llamaDir -IsWin $IsWindows) | Where-Object { Test-Path $_ } | Select-Object -First 1
                if ($llamaServerBin -and (Get-Item $llamaServerBin).Length -gt 0) {
                    Write-Host "[OK] llama.cpp compilado com Vulkan nativo! Binario: $llamaServerBin" -ForegroundColor Green
                    $llamaCppBuildOk = $true
                    $llamaServerBinResolved = $llamaServerBin
                }
            }
        }
    } catch {
        Write-Host "[!] Erro na compilação: $($_.Exception.Message)" -ForegroundColor Yellow
    } finally {
        Pop-Location
    }
}

# =====================================================================
# COMPILAÇÃO DO STABLE-DIFFUSION.CPP
# =====================================================================
Write-Host "`n=== COMPILANDO STABLE-DIFFUSION.CPP (Backend Vulkan para GPU) ===" -ForegroundColor Cyan
 $sdDir = Join-Path $PhoenixRoot "repos\stable-diffusion.cpp"
 $sdBuildOk = $false
 $sdCliBinResolved = $null

function Get-SdCliBinCandidates {
    param([string]$SdDir, [bool]$IsWin)
    if ($IsWin) { return @((Join-Path $SdDir "build\bin\sd-cli.exe"), (Join-Path $SdDir "build\bin\Release\sd-cli.exe")) }
    else { return @((Join-Path $SdDir "build/bin/sd-cli")) }
}

if (Test-Path $sdDir) {
    Push-Location $sdDir
    try {
        if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
            Write-Host "[!] CMake indisponível para stable-diffusion.cpp." -ForegroundColor Yellow
        } elseif ($IsWindows -and -not $vsToolsAvailable) {
            Write-Host "[!] VS Build Tools indisponível para stable-diffusion.cpp." -ForegroundColor Yellow
        } else {
            $cacheFile = Join-Path $sdDir "build\CMakeCache.txt"
            if (Test-Path $cacheFile) {
                $cachedHome = (Select-String -Path $cacheFile -Pattern '^CMAKE_HOME_DIRECTORY:INTERNAL=(.*)$' -ErrorAction SilentlyContinue | ForEach-Object { $_.Matches[0].Groups[1].Value } | Select-Object -First 1)
                if ($cachedHome -and ($cachedHome.TrimEnd('/','\') -ne $sdDir.TrimEnd('/','\'))) {
                    Remove-Item -Recurse -Force (Join-Path $sdDir "build") -ErrorAction SilentlyContinue
                }
            }

            $configureOk = $false
            $buildOk = $false

            if ($IsWindows) {
                $ninjaAvailable = [bool](Get-Command ninja -ErrorAction SilentlyContinue)
                if ($ninjaAvailable) {
                    Write-Host "[*] Usando generator: Ninja (stable-diffusion)" -ForegroundColor DarkGray
                    
                    $vsDevShell = $null
                    if ($vsPath) {
                        $devShellScripts = @(
                            (Join-Path $vsPath "Common7\Tools\Launch-VsDevShell.ps1"),
                            (Join-Path $vsPath "Common7\Tools\Enter-VsDevShell.ps1")
                        )
                        foreach ($script in $devShellScripts) {
                            if (Test-Path $script) { $vsDevShell = $script; break }
                        }
                    }

                    if ($vsDevShell) {
                        Write-Host "[*] Ativando ambiente MSVC via: $vsDevShell" -ForegroundColor DarkGray
                        & $vsDevShell -SkipAutomaticLocation -Arch amd64
                        
                        $clCheck = Get-Command cl.exe -ErrorAction SilentlyContinue
                        if ($clCheck) {
                            Write-Host "[OK] cl.exe resolvido para stable-diffusion." -ForegroundColor Green
                            & cmake -B build -G "Ninja" -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON -DCMAKE_CXX_FLAGS="/bigobj" 2>&1 | Out-Host
                            $configureOk = ($LASTEXITCODE -eq 0)
                            if ($configureOk) {
                                Write-Host "[*] Compilando stable-diffusion.cpp no Windows (Ninja)..."
                                & cmake --build build 2>&1 | Out-Host
                                $buildOk = ($LASTEXITCODE -eq 0)
                            }
                        } else {
                            Write-Host "[!] cl.exe NAO encontrado. Tentando fallback MSBuild..." -ForegroundColor Red
                            & cmake -B build -G $vsGenerator -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON -DCMAKE_CXX_FLAGS="/bigobj" 2>&1 | Out-Host
                            $configureOk = ($LASTEXITCODE -eq 0)
                            if ($configureOk) { & cmake --build build --config Release 2>&1 | Out-Host; $buildOk = ($LASTEXITCODE -eq 0) }
                        }
                    } else {
                        Write-Host "[!] VsDevShell.ps1 não encontrado. Tentando CMake sem ambiente MSVC..." -ForegroundColor Yellow
                        & cmake -B build -G "Ninja" -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON -DCMAKE_CXX_FLAGS="/bigobj" 2>&1 | Out-Host
                        $configureOk = ($LASTEXITCODE -eq 0)
                        if ($configureOk) { & cmake --build build 2>&1 | Out-Host; $buildOk = ($LASTEXITCODE -eq 0) }
                    }
                } else {
                    Write-Host "[!] Ninja não encontrado - usando fallback: $vsGenerator" -ForegroundColor DarkYellow
                    & cmake -B build -G $vsGenerator -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON -DCMAKE_CXX_FLAGS="/bigobj" 2>&1 | Out-Host
                    $configureOk = ($LASTEXITCODE -eq 0)
                    if ($configureOk) { & cmake --build build --config Release 2>&1 | Out-Host; $buildOk = ($LASTEXITCODE -eq 0) }
                }
            } else {
                & cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON 2>&1 | Out-Host
                $configureOk = ($LASTEXITCODE -eq 0)
                if ($configureOk) { $cores = (nproc); & cmake --build build --config Release -j $cores 2>&1 | Out-Host; $buildOk = ($LASTEXITCODE -eq 0) }
            }

            if ($configureOk -and $buildOk) {
                $sdCliBin = (Get-SdCliBinCandidates -SdDir $sdDir -IsWin $IsWindows) | Where-Object { Test-Path $_ } | Select-Object -First 1
                if ($sdCliBin -and (Get-Item $sdCliBin).Length -gt 0) {
                    Write-Host "[OK] stable-diffusion.cpp compilado com Vulkan nativo! Binario: $sdCliBin" -ForegroundColor Green
                    $sdBuildOk = $true
                    $sdCliBinResolved = $sdCliBin
                }
            }
        }
    } catch {
        Write-Host "[!] Erro na compilação do stable-diffusion: $($_.Exception.Message)" -ForegroundColor Yellow
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[!] Repositório stable-diffusion.cpp não encontrado. Pulando compilação." -ForegroundColor DarkYellow
}

# =====================================================================
# CONTAINERS DOCKER (Ollama + Open WebUI + ONLYOFFICE + Tika)
# =====================================================================
Write-Host "`n=== PROVISIONAMENTO DE CONTAINERS ===" -ForegroundColor Cyan

Write-Host "[*] Provisionando Ollama (porta 11434)..."
& docker volume create ollama 2>&1 | Out-Null
& docker rm -f ollama 2>&1 | Out-Null
& docker run -d --name ollama --restart unless-stopped -p 11434:11434 -e OLLAMA_ORIGINS="*" -v ollama:/root/.ollama ollama/ollama 2>&1 | Out-Null

if (-not $llamaCppBuildOk) {
    Write-Host "[*] llama.cpp indisponivel - baixando qwen3:8b pro Ollama..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    & docker exec ollama ollama pull qwen3:8b 2>&1 | Out-Null
}

 $enginePrefPath = Join-Path $env:ProgramData "Phoenix\engine_preference.json"
 $enginePrefDir = Split-Path $enginePrefPath -Parent
if (-not (Test-Path $enginePrefDir)) { New-Item -ItemType Directory -Force -Path $enginePrefDir | Out-Null }
 $binExists = $false
if ($llamaServerBinResolved -and (Test-Path $llamaServerBinResolved) -and (Get-Item $llamaServerBinResolved).Length -gt 0) {
    $binExists = $true
} else {
    $llamaDirForCheck = Join-Path $PhoenixRoot "repos\llama.cpp"
    $candidatesForCheck = @((Join-Path $llamaDirForCheck "build\bin\llama-server.exe"), (Join-Path $llamaDirForCheck "build\bin\Release\llama-server.exe"))
    foreach ($c in $candidatesForCheck) {
        if ((Test-Path $c) -and (Get-Item $c).Length -gt 0) { $binExists = $true; $llamaServerBinResolved = $c; break }
    }
}
 $preferredEngine = if ($binExists) { "llama.cpp" } else { "ollama" }
@{ preferred_llm_engine = $preferredEngine; llama_cpp_build_ok = $binExists; llama_server_bin = $llamaServerBinResolved } | ConvertTo-Json | Set-Content -Path $enginePrefPath -Encoding UTF8

Write-Host "[*] Provisionando Open WebUI (porta 8010)..."
& docker volume create open-webui 2>&1 | Out-Null
& docker rm -f open_webui 2>&1 | Out-Null
& docker run -d --name open_webui --restart unless-stopped -p 8010:8080 --add-host=host.docker.internal:host-gateway -e OLLAMA_BASE_URL=http://host.docker.internal:11434 -e OPENAI_API_BASE_URL=http://host.docker.internal:8081/v1 -e OPENAI_API_KEY=llama-cpp-local -v open-webui:/app/backend/data ghcr.io/open-webui/open-webui:main 2>&1 | Out-Null

# PHX-REVERT: ONLYOFFICE Docs Server + Apache Tika Server removidos daqui.
# A Document Engine da Phoenix ficou definida como "IA lê/entende/resume/
# edita/cria" via pymupdf4llm+python-docx+openpyxl+python-pptx (puro
# Python, já instalado acima) - sem editor visual embutido, então esses
# dois containers Docker (que juntos consomem ~1.5-2GB de RAM ociosos)
# não são necessários. Se um editor visual tipo Word-no-browser virar
# requisito no futuro, reintroduzir aqui.

# =====================================================================
# PHOENIX STUDIO (Node.js)
# =====================================================================
Write-Host "`n=== INICIANDO PHOENIX STUDIO (NODE.JS) ===" -ForegroundColor Cyan
 $studioDir = Join-Path $PhoenixRoot "repos\phoenix_studio"
if (-not (Test-Path $studioDir)) { $studioDir = Join-Path $PhoenixRoot "platform_source" }
if (Test-Path $studioDir) {
    Push-Location $studioDir
    if (Test-Path "package.json") {
        & npm install 2>&1 | Out-Host
        if ($IsWindows) { Start-Process -FilePath "npm" -ArgumentList "run dev" -WindowStyle Hidden }
        else { Start-Process -FilePath "npm" -ArgumentList "run dev" -NoNewWindow }
    }
    Pop-Location
}

# =====================================================================
# SEARXNG
# =====================================================================
Write-Host "`n=== CONFIGURANDO STACK SEARXNG ===" -ForegroundColor Cyan
 $searxBase = Join-Path $PhoenixRoot "searxng-docker"
docker stop searxng searxng-phoenix searxng-webui 2>$null | Out-Null
docker rm searxng searxng-phoenix searxng-webui 2>$null | Out-Null
Remove-Item -Recurse -Force $searxBase -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $searxBase | Out-Null
Set-Content -Path (Join-Path $searxBase "docker-compose.yml") -Encoding UTF8 -Value @"
services:
  searxng-phoenix:
    container_name: searxng-phoenix
    image: searxng/searxng:latest
    ports: ["8080:8080"]
    volumes: ["./searxng-phoenix:/etc/searxng:rw"]
    restart: unless-stopped
  searxng-webui:
    container_name: searxng-webui
    image: searxng/searxng:latest
    ports: ["8088:8080"]
    volumes: ["./searxng-webui:/etc/searxng:rw"]
    restart: unless-stopped
"@
Push-Location $searxBase
docker compose up -d 2>&1 | Out-Null
Start-Sleep -Seconds 10
Pop-Location

# =====================================================================
# DOWNLOAD DOS MODELOS GGUF
# =====================================================================
Write-Host "`n=== PREPARANDO MODELOS GGUF (LLM + VISAO) ===" -ForegroundColor Cyan
 $workspaceDir = if ($PhoenixWorkspace) { $PhoenixWorkspace } elseif ($env:PHOENIX_WORKSPACE) { $env:PHOENIX_WORKSPACE } else { Join-Path $PhoenixRoot "Workstations" }
 $modelsBaseDir = Join-Path $workspaceDir "Models\Chat\GGUF"
if (-not (Test-Path $modelsBaseDir)) { New-Item -ItemType Directory -Force -Path $modelsBaseDir | Out-Null }

function Download-GGUF {
    param([string]$Name, [string]$Url, [string]$Dest)
    if (Test-Path $Dest) {
        $fileSize = (Get-Item $Dest).Length / 1GB
        Write-Host "[OK] $Name já existe em disco ($([math]::Round($fileSize, 2)) GB)." -ForegroundColor Green
        return
    }
    Write-Host "[*] Baixando $Name..." -ForegroundColor Yellow
    try {
        if ($IsWindows) { Start-BitsTransfer -Source $Url -Destination $Dest }
        else { Invoke-WebRequest -Uri $Url -OutFile $Dest -UseBasicParsing }
        Write-Host "[OK] $Name baixado com sucesso!" -ForegroundColor Green
    } catch {
        Write-Host "[X] Falha ao baixar ${Name}: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 1. Qwen3 8B (Modelo LLM principal para raciocínio em CPU)
Download-GGUF -Name "Qwen3 8B (LLM)" `
    -Url "https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q4_K_M.gguf" `
    -Dest (Join-Path $modelsBaseDir "qwen3-8b-q4_k_m.gguf")

# 2. MiniCPM-V 2.6 (Modelo Multimodal para Visão)
Download-GGUF -Name "MiniCPM-V 2.6 (Vision)" `
    -Url "https://huggingface.co/bartowski/MiniCPM-V-2_6-GGUF/resolve/main/MiniCPM-V-2_6-Q6_K_L.gguf?download=true" `
    -Dest (Join-Path $modelsBaseDir "MiniCPM-V-2_6-Q6_K_L.gguf")

# 3. MMProj (Projetor de Imagens - OBRIGATÓRIO para o MiniCPM-V enxergar)
Download-GGUF -Name "MMProj (Vision Encoder)" `
    -Url "https://huggingface.co/openbmb/MiniCPM-V-2_6-gguf/resolve/main/mmproj-model-f16.gguf?download=true" `
    -Dest (Join-Path $modelsBaseDir "mmproj-model-f16.gguf")

# =====================================================================
# BOOT DA API
# =====================================================================
Write-Host "`n=== INICIANDO PHOENIX ENGINE ===" -ForegroundColor Green
 $pythonExe = if ($IsWindows) { ".\.venv\Scripts\python.exe" } else { ".\.venv/bin/python" }
 $proc = Start-Process $pythonExe -ArgumentList "api_server.py" -PassThru -NoNewWindow

 $apiReady = $false
# PHX-FIX: Aumentado o timeout de 60s (30) para 300s (150) para dar conta do npm install da Aviary no primeiro boot
for ($i = 1; $i -le 150; $i++) {
    Start-Sleep -Seconds 2
    if ($proc.HasExited) { return (& $failContract "api_server encerrou prematuramente." "PX012") }
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 2
        if ($response.status -eq "healthy") { $apiReady = $true; break }
    } catch {}
}

if ($apiReady) {
    return @{ Name="Common"; Version="7.1.0"; Success=$true; ErrorCode=""; Warnings=@(); Errors=@(); RestartRequired=$false; Artifacts=@("api_server", "llama_cpp_vulkan", "python_runtime", "searxng-phoenix", "searxng-webui", "phoenix_studio", "open_webui"); Timestamp=Get-Date }
} else {
    return (& $failContract "API nao respondeu ao health check." "PX013")
}