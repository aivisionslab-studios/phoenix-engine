# install_phoenix.ps1
# Bootstrapper Oficial da Phoenix Engine 4.0
# Filosofia: Winget (Sistema) > Git (Motores/Codigo) > Docker (Execucao)

# >>> CORRECAO CRITICA DEFINITIVA <<<
# NAO usar $ErrorActionPreference = "Stop" como padrao global.
# Motivo real do travamento: quando um comando nativo (docker/git/winget)
# escreve no stderr e essa saida e redirecionada com "*>" ou "2>", o
# PowerShell converte cada linha em um ErrorRecord. Com ErrorActionPreference
# = "Stop", QUALQUER ErrorRecord vira excecao fatal imediata - mesmo que a
# intencao fosse so silenciar/ignorar aquela saida. Foi isso que matou o
# script exatamente no "docker info *> $null": o Docker Desktop nao estava
# rodando, o docker.exe escreveu o erro de conexao no stderr, o "*>" virou
# ErrorRecord, e o "Stop" abortou tudo na primeira tentativa (nunca chegou
# a rodar as 20 tentativas do loop de espera).
# A partir de agora: ErrorActionPreference = "Continue" (comportamento
# nativo do PowerShell) e cada etapa critica checa $LASTEXITCODE manualmente.
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"   # evita barras de progresso do Invoke-WebRequest lentas

# Impede que "git clone/pull" fique esperando usuario/senha indefinidamente
# quando um repo e privado ou nao existe (foi exatamente o que aconteceu com
# AIVisionsLab/Phoenix.git). Sem isso, o git abre um prompt de credencial
# que pode travar o script "para sempre" em vez de so retornar erro.
$env:GIT_TERMINAL_PROMPT = "0"

try {

# 1. Auto-Elevacao para Administrador
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[!] Solicitando privilegios de administrador..." -ForegroundColor Yellow
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Set-Location $PSScriptRoot
Write-Host "[OK] Executando como Administrador em: $PWD" -ForegroundColor Green

# 2. Instalacao de Pre-Requisitos via Winget (Camada de Sistema)
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "[X] Winget nao encontrado. Atualize seu Windows pela Microsoft Store (App Installer)." -ForegroundColor Red
    Pause
    exit
}

Write-Host "`n=== INSTALACAO DE PRE-REQUISITOS (WINGET) ===" -ForegroundColor Cyan

# Python: SEMPRE reinstala/repara, mesmo se ja existir, forcando PATH e InstallAllUsers.
Write-Host "[*] Reinstalando/Reparando Python 3.12 (forcado, com PATH garantido)..." -ForegroundColor Yellow
winget install -e --id Python.Python.3.12 `
    --accept-package-agreements --accept-source-agreements `
    --force --disable-interactivity --scope machine `
    --silent `
    --override "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_launcher=1"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Winget retornou codigo $LASTEXITCODE para Python. Tentando fallback sem --override..." -ForegroundColor DarkYellow
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --force --scope machine
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Fallback tambem retornou codigo $LASTEXITCODE. Verifique manualmente apos o script." -ForegroundColor DarkYellow
    }
}

$PythonRoots = @("C:\Program Files\Python312", "C:\Program Files\Python312\Scripts")
foreach ($root in $PythonRoots) {
    if (Test-Path $root) {
        $machinePath = [System.Environment]::GetEnvironmentVariable("Path","Machine")
        if ($machinePath -notlike "*$root*") {
            Write-Host "[*] Adicionando $root ao PATH de sistema..." -ForegroundColor Cyan
            [System.Environment]::SetEnvironmentVariable("Path", "$machinePath;$root", "Machine")
        }
    }
}

$WingetPackages = @(
    @{Name="Git"; ID="Git.Git"; Cmd="git"},
    @{Name="Docker Desktop"; ID="Docker.DockerDesktop"; Cmd="docker"},
    @{Name=".NET SDK 9.0"; ID="Microsoft.DotNet.SDK.9"; Cmd="dotnet"},
    @{Name="PowerShell"; ID="Microsoft.PowerShell"; Cmd="pwsh"},
    @{Name="Vulkan SDK"; ID="KhronosGroup.VulkanSDK"; Cmd="vulkaninfo"},
    @{Name="Visual Studio Build Tools"; ID="Microsoft.VisualStudio.2022.BuildTools"; Cmd="vswhere"},
    @{Name="FFmpeg"; ID="Gyan.FFmpeg"; Cmd="ffmpeg"},
    @{Name="Tesseract OCR"; ID="UB-Mannheim.TesseractOCR"; Cmd="tesseract"},
    @{Name="NodeJS LTS"; ID="OpenJS.NodeJS.LTS"; Cmd="node"},
    @{Name="PowerToys"; ID="Microsoft.PowerToys"; Cmd="powertoys"},
    @{Name="GitHub Desktop"; ID="GitHub.GitHubDesktop"; Cmd="github"},
    @{Name="VLC"; ID="VideoLAN.VLC"; Cmd="vlc"},
    @{Name="Firefox"; ID="Mozilla.Firefox"; Cmd="firefox"},
    @{Name="Chrome"; ID="Google.Chrome"; Cmd="chrome"}
)

foreach ($pkg in $WingetPackages) {
    Write-Host "[*] Verificando $($pkg.Name)..."
    if ($pkg.Cmd -and (Get-Command $pkg.Cmd -ErrorAction SilentlyContinue)) {
        Write-Host "[OK] $($pkg.Name) ja instalado." -ForegroundColor Green
    } else {
        Write-Host "[*] Instalando $($pkg.Name)..." -ForegroundColor Yellow
        winget install -e --id $pkg.ID --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[!] Winget retornou codigo $LASTEXITCODE para $($pkg.Name). Prosseguindo mesmo assim." -ForegroundColor DarkYellow
        }
        if ($pkg.Name -eq "Docker Desktop") {
            Write-Host "[!] Docker Desktop acabou de ser instalado pela primeira vez." -ForegroundColor Yellow
            Write-Host "[!] Recomendado: REINICIE O PC agora para habilitar WSL2/Hyper-V, depois rode o script de novo." -ForegroundColor Red
            Pause
            exit
        }
    }
}

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "[*] Validando Python no PATH da sessao atual..." -ForegroundColor Cyan
$pythonCheck = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCheck) {
    Write-Host "[X] Python ainda nao esta reconhecido no PATH desta sessao mesmo apos reinstalacao forcada." -ForegroundColor Red
    Write-Host "    Provavel causa: alias de execucao do Windows (python.exe redirecionando para a Store)." -ForegroundColor Red
    Write-Host "    Va em Configuracoes > Aplicativos > Aliases de execucao de aplicativos e desative o 'python.exe' da Store." -ForegroundColor Red
    Pause
    exit
} else {
    Write-Host "[OK] Python encontrado em: $($pythonCheck.Source)" -ForegroundColor Green
    python --version
}

# 3. Verifica se o api_server.py esta na pasta
if (-not (Test-Path ".\api_server.py")) {
    Write-Host "[X] Arquivo api_server.py nao encontrado nesta pasta! O codigo fonte da Phoenix esta faltando." -ForegroundColor Red
    Pause
    exit
}

# 4. Configuracao do Ambiente Python (Wrapper de Interoperabilidade)
Write-Host "`n=== CONFIGURACAO DO KERNEL (PYTHON) ===" -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install fastapi uvicorn psutil chromadb pythonnet HardwareMonitor wmi pywin32 astor

# ---------------------------------------------------------------------------
# 4b. SELF-TEST DOS SENSORES DE GPU (novo)
# ---------------------------------------------------------------------------
# Roda um teste real e imprime na tela AGORA, durante a instalacao, se os
# sensores de GPU vao funcionar quando a API abrir. Nao inventa numero: ou
# le o sensor de verdade, ou avisa exatamente qual etapa falhou.
Write-Host "`n=== SELF-TEST: SENSORES DE GPU (HardwareMonitor) ===" -ForegroundColor Cyan

$selfTestScript = @'
import sys
try:
    import clr
except ImportError:
    print("[X] pythonnet nao instalado.")
    sys.exit(1)

try:
    from HardwareMonitor.Hardware import Computer
except ImportError:
    print("[X] pacote HardwareMonitor nao instalado.")
    sys.exit(1)
except Exception as e:
    print(f"[X] pythonnet nao conseguiu carregar HardwareMonitor.Hardware: {e}")
    sys.exit(1)

try:
    computer = Computer()
    computer.IsGpuEnabled = True
    computer.Open()
except Exception as e:
    print(f"[X] falha ao abrir Computer(): {e}")
    sys.exit(1)

gpu_found = False
sensor_found = False
for hw in computer.Hardware:
    hw.Update()
    if "Gpu" in str(hw.HardwareType):
        gpu_found = True
        sensors = list(hw.Sensors)
        print(f"[i] GPU detectada: {hw.Name} ({len(sensors)} sensor(es))")
        for s in sensors:
            print(f"    - {s.Name} [{s.SensorType}] = {s.Value}")
            sensor_found = True

if not gpu_found:
    print("[X] Nenhuma GPU foi detectada pelo HardwareMonitor.")
    sys.exit(1)
if not sensor_found:
    print("[X] GPU detectada mas SEM sensores. Rode este script como Administrador.")
    sys.exit(1)

print("[OK] Sensores de GPU funcionando.")
sys.exit(0)
'@

$selfTestPath = Join-Path $env:TEMP "phoenix_gpu_selftest.py"
Set-Content -Path $selfTestPath -Value $selfTestScript -Encoding UTF8

python $selfTestPath
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Self-test de sensores passou. A API deve abrir com sensores de GPU funcionando." -ForegroundColor Green
} else {
    Write-Host "[!] Self-test de sensores FALHOU (ver mensagens acima)." -ForegroundColor Red
    Write-Host "    A API ainda vai abrir, mas os campos de GPU (temp/load/VRAM) vao aparecer como 'INDISPONIVEL'." -ForegroundColor Yellow
    Write-Host "    Causas mais comuns: (1) driver AMD desatualizado/sem ADL, (2) script nao esta rodando" -ForegroundColor Yellow
    Write-Host "    como Administrador (ele deveria estar - Secao 1 ja se auto-eleva)." -ForegroundColor Yellow
}
Remove-Item $selfTestPath -ErrorAction SilentlyContinue

# 5. Provisionamento de Containers Docker (Camada de Execucao)
Write-Host "`n=== PROVISIONAMENTO DE CONTAINERS ===" -ForegroundColor Cyan

# --- Funcao auxiliar: roda um comando nativo sem deixar o stderr virar excecao ---
# Captura tudo (stdout+stderr) numa variavel em vez de deixar fluir pro host,
# e retorna o texto + expõe $LASTEXITCODE normalmente. Isso evita 100% do
# problema de ErrorRecord/terminating error, independente do ErrorActionPreference.
function Invoke-Native {
    param([Parameter(Mandatory)][string]$Exe, [Parameter(Mandatory)][string[]]$Args)
    $output = & $Exe @Args 2>&1 | ForEach-Object { $_.ToString() }
    return @{ Output = $output; ExitCode = $LASTEXITCODE }
}

# --- Garante que o Docker Desktop esta rodando; se nao estiver, tenta abrir ---
Write-Host "[*] Verificando se o Docker Desktop esta ativo..."
$dockerReady = $false
$check = Invoke-Native -Exe "docker" -Args @("info")
if ($check.ExitCode -eq 0) {
    $dockerReady = $true
    Write-Host "[OK] Docker daemon ja estava ativo." -ForegroundColor Green
} else {
    Write-Host "[!] Docker daemon nao respondeu. Tentando iniciar o Docker Desktop..." -ForegroundColor Yellow

    $dockerExePaths = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe"
    )
    $dockerExe = $dockerExePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $dockerExe) {
        Write-Host "[X] Nao encontrei o executavel do Docker Desktop nos caminhos padrao." -ForegroundColor Red
        Write-Host "    Verificados: $($dockerExePaths -join ' | ')" -ForegroundColor Red
        Pause
        exit
    }

    # IMPORTANTE: o Docker Desktop precisa rodar na sessao do usuario logado,
    # nao como Administrador elevado. Se este script foi elevado via UAC,
    # tentamos lancar o processo sem forcar elevacao adicional; se o daemon
    # ainda assim nao subir, avisamos o usuario para abrir manualmente 1x
    # (depois disso o Docker fica com "iniciar ao logar" ligado por padrao).
    Write-Host "[*] Iniciando: $dockerExe" -ForegroundColor Cyan
    Start-Process -FilePath $dockerExe | Out-Null

    Write-Host "[*] Aguardando o Docker Desktop subir (isso pode levar 1-2 minutos na primeira vez)..." -ForegroundColor Yellow
    for ($i = 1; $i -le 40; $i++) {
        Start-Sleep -Seconds 3
        $check = Invoke-Native -Exe "docker" -Args @("info")
        if ($check.ExitCode -eq 0) {
            $dockerReady = $true
            Write-Host "[OK] Docker daemon respondeu apos $($i * 3)s." -ForegroundColor Green
            break
        }
        Write-Host "    Aguardando... ($i/40)" -ForegroundColor DarkGray
    }
}

if (-not $dockerReady) {
    Write-Host "[X] Docker Desktop nao respondeu a tempo." -ForegroundColor Red
    Write-Host "    Abra o Docker Desktop manualmente pela primeira vez (aceite os termos/permissoes" -ForegroundColor Red
    Write-Host "    de rede que ele pedir), espere a baleia ficar verde na bandeja, e rode o script de novo." -ForegroundColor Red
    Pause
    exit
}

# Ollama
Write-Host "[*] Provisionando Ollama..."
Invoke-Native -Exe "docker" -Args @("volume","create","ollama") | Out-Null
Invoke-Native -Exe "docker" -Args @("rm","-f","ollama") | Out-Null
$run = Invoke-Native -Exe "docker" -Args @("run","-d","--name","ollama","--restart","unless-stopped","-p","11434:11434","-v","ollama:/root/.ollama","ollama/ollama")
if ($run.ExitCode -ne 0) {
    Write-Host "[X] Falha ao subir o container do Ollama (codigo $($run.ExitCode))." -ForegroundColor Red
    Write-Host ($run.Output -join "`n") -ForegroundColor DarkGray
    Pause
    exit
}
Write-Host "[OK] Container Ollama no ar." -ForegroundColor Green

Write-Host "[*] Baixando modelo qwen3:8b para o Ollama (isso pode demorar alguns minutos)..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Streama a saida em tempo real (progresso do pull) usando & diretamente,
# mas com ErrorActionPreference = Continue (ja setado globalmente) entao
# stderr NAO vira excecao - so aparece na tela normalmente.
docker exec ollama ollama pull qwen3:8b
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] O pull do modelo qwen3:8b retornou codigo $LASTEXITCODE (rede/timeout). Prosseguindo mesmo assim." -ForegroundColor DarkYellow
} else {
    Write-Host "[OK] Modelo qwen3:8b baixado." -ForegroundColor Green
}

# Open WebUI
Write-Host "[*] Provisionando Open WebUI..."
Invoke-Native -Exe "docker" -Args @("volume","create","open-webui") | Out-Null
Invoke-Native -Exe "docker" -Args @("rm","-f","open_webui") | Out-Null
$runWebui = Invoke-Native -Exe "docker" -Args @("run","-d","--name","open_webui","--restart","unless-stopped","-p","3000:8080","--add-host=host.docker.internal:host-gateway","-e","OLLAMA_BASE_URL=http://host.docker.internal:11434","-v","open-webui:/app/backend/data","ghcr.io/open-webui/open-webui:main")
if ($runWebui.ExitCode -ne 0) {
    Write-Host "[!] Falha ao subir o Open WebUI (codigo $($runWebui.ExitCode)). Prosseguindo mesmo assim." -ForegroundColor DarkYellow
    Write-Host ($runWebui.Output -join "`n") -ForegroundColor DarkGray
} else {
    Write-Host "[OK] Container Open WebUI no ar (http://localhost:3000)." -ForegroundColor Green
}

# 6. Clonagem de Motores de IA e Codigo Oficial via Git
Write-Host "`n=== CLONAGEM DE REPOSITORIOS OFICIAIS (GIT) ===" -ForegroundColor Cyan

$Repos = @{
    # "Phoenix"            = "https://github.com/AIVisionsLab/Phoenix.git"  # ainda nao existe - reative quando criar o repo
    "OpenWebUI"            = "https://github.com/open-webui/open-webui.git"
    "ComfyUI"              = "https://github.com/comfyanonymous/ComfyUI.git"
    "llama.cpp"            = "https://github.com/ggml-org/llama.cpp.git"
    "stable-diffusion.cpp" = "https://github.com/leejet/stable-diffusion.cpp.git"
    "LibreHardwareMonitor" = "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor.git"
    "Ollama"               = "https://github.com/ollama/ollama.git"
    "Whisper.cpp"          = "https://github.com/ggml-org/whisper.cpp.git"
}

if (-not (Test-Path ".\repos")) {
    New-Item -ItemType Directory -Force -Path ".\repos" | Out-Null
}

foreach ($repo in $Repos.Keys) {
    $dest = Join-Path ".\repos" $repo
    if (!(Test-Path $dest)) {
        Write-Host "[*] Clonando $repo..." -ForegroundColor Yellow
        git clone $Repos[$repo] $dest
    } else {
        Write-Host "[*] Atualizando $repo..." -ForegroundColor Green
        git -C $dest pull
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Git retornou codigo $LASTEXITCODE para $repo. Prosseguindo mesmo assim." -ForegroundColor DarkYellow
    }
}

# >>> NOTA IMPORTANTE (removido apos diagnostico) <<<
# Havia aqui uma secao que compilava um projeto .NET proprio referenciando
# LibreHardwareMonitorLib via NuGet. Foi removida porque o api_server.py
# NAO usa esse caminho: o kernel importa diretamente o pacote pip
# "HardwareMonitor" (from HardwareMonitor.Hardware import ...), que ja
# embute a LibreHardwareMonitorLib.dll dentro do proprio wheel. A correcao
# real dos sensores e simplesmente ter "HardwareMonitor" na linha de
# pip install da Secao 4 (ja adicionado acima). Compilar um .csproj a parte
# nao tinha efeito nenhum no runtime real e so desperdicava ~20-30s por
# execucao. Se no futuro a Phoenix migrar para carregar uma DLL propria via
# pythonnet.clr.AddReference, essa secao de compilacao NuGet volta a fazer
# sentido e pode ser restaurada.
#
# LibreHardwareMonitor/HardwareMonitor no Windows precisa rodar elevado para
# ler a maioria dos sensores (temperatura, voltagem, etc). Como este script
# ja roda como Administrador (Secao 1), o api_server.py herdando este
# contexto satisfaz esse requisito automaticamente.
#
# Para sensores de placa-mae (alguns modelos), pode ainda ser necessario o
# driver PawnIO: winget install -e --id PawnIO.PawnIO

# 7. Inicializacao da Phoenix (A API assume o controle e abre o navegador)
Write-Host "`n=== INICIANDO PHOENIX ENGINE ===" -ForegroundColor Green
Write-Host "[*] O PowerShell concluiu o provisionamento. Passando o controle para a API Python..." -ForegroundColor DarkGray
Write-Host "[*] Pressione Ctrl+C para parar o servidor." -ForegroundColor DarkGray

python api_server.py

}
catch {
    Write-Host "`n[X] ERRO FATAL DURANTE O PROVISIONAMENTO:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "`nLinha: $($_.InvocationInfo.ScriptLineNumber)" -ForegroundColor DarkGray
}
finally {
    Write-Host "`n[*] Script finalizado. Pressione qualquer tecla para fechar esta janela..." -ForegroundColor DarkGray
    Pause
}