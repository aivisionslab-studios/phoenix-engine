# install/windows.ps1
# Camada exclusiva do Windows: winget, PATH de sistema, pywin32/wmi/
# HardwareMonitor (interop .NET), Docker Desktop, self-test de sensores
# via LibreHardwareMonitor. Nada aqui roda no Linux.
#
# NAO faz auto-elevacao aqui - o install_phoenix.ps1 (Secao 2) ja garante
# que chegamos neste arquivo como Administrador. Duplicar a checagem
# geraria um segundo prompt de UAC sem necessidade.

Write-Host "[OK] Executando como Administrador em: $PWD" -ForegroundColor Green

# 1. Instalacao de Pre-Requisitos via Winget (Camada de Sistema)
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

if (-not (Test-Path ".\api_server.py")) {
    Write-Host "[X] Arquivo api_server.py nao encontrado nesta pasta! O codigo fonte da Phoenix esta faltando." -ForegroundColor Red
    Pause
    exit
}

# Dependencias Python EXCLUSIVAS do Windows (interop com LibreHardwareMonitor)
Write-Host "`n=== DEPENDENCIAS PYTHON EXCLUSIVAS DO WINDOWS ===" -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install pythonnet HardwareMonitor wmi pywin32

# Self-test de sensores de GPU via LibreHardwareMonitor (so existe no Windows;
# no Linux a leitura equivalente e feita via sysfs em install/linux.ps1)
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

$selfTestPath = Join-Path $env:TEMP "phoenix_gpu_selftest_windows.py"
Set-Content -Path $selfTestPath -Value $selfTestScript -Encoding UTF8

python $selfTestPath
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Self-test de sensores passou. A API deve abrir com sensores de GPU funcionando." -ForegroundColor Green
} else {
    Write-Host "[!] Self-test de sensores FALHOU (ver mensagens acima)." -ForegroundColor Red
    Write-Host "    A API ainda vai abrir, mas os campos de GPU (temp/load/VRAM) vao aparecer como 'INDISPONIVEL'." -ForegroundColor Yellow
    Write-Host "    Causas mais comuns: (1) driver AMD desatualizado/sem ADL, (2) script nao esta rodando como Administrador." -ForegroundColor Yellow
}
Remove-Item $selfTestPath -ErrorAction SilentlyContinue

# Move o data-root do Docker Desktop (imagens, volumes, containers) para o
# disco recomendado pelo storage_scanner.ps1, usando o mecanismo oficial do
# WSL2 pra isso ("wsl --manage <distro> --move <caminho>"). So mexe se o
# Docker Desktop realmente estiver usando o backend WSL2 (padrao desde 2021)
# e se essa versao do WSL suportar o comando --manage. Pede confirmacao
# porque para o Docker Desktop e o WSL antes de mover.
function Move-DockerDataRoot {
    param([string]$TargetDrive)

    if (-not $TargetDrive) { return }

    Write-Host "`n=== DADOS DO DOCKER ===" -ForegroundColor Cyan

    if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
        Write-Host "[!] wsl.exe nao encontrado - Docker Desktop provavelmente nao usa o backend WSL2 nesta maquina. Pulando." -ForegroundColor DarkYellow
        return
    }

    $distros = (wsl -l -q 2>&1 | Out-String)
    if ($distros -notmatch "docker-desktop-data") {
        Write-Host "[!] Distro 'docker-desktop-data' nao encontrada no WSL (Docker Desktop pode nao ter rodado ainda 1x). Pulando." -ForegroundColor DarkYellow
        return
    }

    $wslHelp = (wsl --help 2>&1 | Out-String)
    if ($wslHelp -notmatch "--manage") {
        Write-Host "[!] Sua versao do WSL nao suporta 'wsl --manage --move'." -ForegroundColor DarkYellow
        Write-Host "    Atualize com: wsl --update" -ForegroundColor DarkYellow
        Write-Host "    Ou mova manualmente em Docker Desktop > Settings > Resources > Advanced." -ForegroundColor DarkYellow
        return
    }

    if (-not (Test-Path $TargetDrive)) {
        Write-Host "[X] Unidade $TargetDrive nao encontrada. Pulando movimentacao de dados do Docker." -ForegroundColor Red
        return
    }

    $targetPath = Join-Path $TargetDrive "DockerData"

    $resp = Read-Host "Mover os dados do Docker (imagens/volumes/containers) para $targetPath ? Isso reinicia o Docker Desktop e o WSL. (S/N)"
    if ($resp -notmatch '^[SsYy]') {
        Write-Host "[i] Movimentacao cancelada. Continuando com os dados na localizacao atual." -ForegroundColor DarkGray
        return
    }

    New-Item -ItemType Directory -Force -Path $targetPath | Out-Null

    Write-Host "[*] Encerrando Docker Desktop e WSL antes de mover os dados..." -ForegroundColor Yellow
    Get-Process "Docker Desktop" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    wsl --shutdown

    Write-Host "[*] Movendo docker-desktop-data para $targetPath (pode demorar dependendo do tamanho dos volumes existentes)..." -ForegroundColor Yellow
    $moveOutput = wsl --manage docker-desktop-data --move $targetPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[X] Falha ao mover os dados do Docker (codigo $LASTEXITCODE)." -ForegroundColor Red
        Write-Host ($moveOutput | Out-String) -ForegroundColor DarkGray
        Write-Host "    Os dados NAO foram movidos - o Docker Desktop deve continuar funcionando normalmente na localizacao original." -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Dados do Docker movidos para $targetPath." -ForegroundColor Green
    }

    # Reabre o Docker Desktop - o bloco logo abaixo (verificacao do daemon)
    # ja cuida de esperar ele voltar a responder.
    $dockerExePaths = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe"
    )
    $dockerExe = $dockerExePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($dockerExe) {
        Start-Process -FilePath $dockerExe | Out-Null
    }
}

if ($Global:PhoenixBestDisk) {
    Move-DockerDataRoot -TargetDrive $Global:PhoenixBestDisk.Path
}

# Garante que o Docker Desktop esta rodando (equivalente Windows do
# "systemctl start docker" do Linux, que fica em install/linux.ps1)
Write-Host "`n=== DOCKER DESKTOP ===" -ForegroundColor Cyan
& docker info 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
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

    # Importante: o Docker Desktop precisa rodar na sessao do usuario logado,
    # nao como Administrador elevado. Se este script foi elevado via UAC e
    # o daemon ainda assim nao subir, o usuario precisa abrir manualmente 1x
    # (depois disso o Docker liga sozinho ao logar, por padrao).
    Write-Host "[*] Iniciando: $dockerExe" -ForegroundColor Cyan
    Start-Process -FilePath $dockerExe | Out-Null

    Write-Host "[*] Aguardando o Docker Desktop subir (isso pode levar 1-2 minutos na primeira vez)..." -ForegroundColor Yellow
    $dockerReady = $false
    for ($i = 1; $i -le 40; $i++) {
        Start-Sleep -Seconds 3
        & docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            Write-Host "[OK] Docker daemon respondeu apos $($i * 3)s." -ForegroundColor Green
            break
        }
        Write-Host "    Aguardando... ($i/40)" -ForegroundColor DarkGray
    }

    if (-not $dockerReady) {
        Write-Host "[X] Docker Desktop nao respondeu a tempo." -ForegroundColor Red
        Write-Host "    Abra o Docker Desktop manualmente pela primeira vez (aceite os termos/permissoes" -ForegroundColor Red
        Write-Host "    de rede que ele pedir), espere a baleia ficar verde na bandeja, e rode o script de novo." -ForegroundColor Red
        Pause
        exit
    }
}
