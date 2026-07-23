# install/linux.ps1
# Camada exclusiva do Linux (alvo: Ubuntu 26.04, mas deve funcionar em
# qualquer Debian/Ubuntu com apt-get): checagem de root, apt, docker.io,
# drivers Vulkan via Mesa/RADV (gratis, suportados desde 2016/2017), e
# self-test de sensores de GPU via sysfs. Nada aqui roda no Windows.

# 1. Verificacao de privilegio (root/sudo)
$currentUid = (id -u)
if ($currentUid -ne "0") {
    Write-Host "[X] Este instalador precisa rodar como root." -ForegroundColor Red
    Write-Host "    Rode novamente com:" -ForegroundColor Red
    Write-Host "    sudo pwsh ./install_phoenix.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Executando como root em: $PWD" -ForegroundColor Green

# 2. Instalacao de Pre-Requisitos via APT (Camada de Sistema)
if (-not (Get-Command apt-get -ErrorAction SilentlyContinue)) {
    Write-Host "[X] apt-get nao encontrado. Este instalador Linux assume Ubuntu/Debian." -ForegroundColor Red
    exit 1
}

Write-Host "`n=== INSTALACAO DE PRE-REQUISITOS (APT) ===" -ForegroundColor Cyan

Write-Host "[*] Atualizando indices do apt..." -ForegroundColor Yellow
apt-get update -y
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] apt-get update retornou codigo $LASTEXITCODE. Prosseguindo mesmo assim." -ForegroundColor DarkYellow
}

# Mapeamento dos pacotes winget originais pro mundo apt:
#   Docker Desktop            -> docker.io + docker-compose-plugin (engine puro, sem GUI)
#   Vulkan SDK                -> mesa-vulkan-drivers + vulkan-tools (RADV, de graca desde 2016/17)
#   Visual Studio Build Tools -> build-essential
#   PowerToys / GitHub Desktop -> sem equivalente direto, pulados de proposito
$AptPackages = @(
    @{Name="Git"; Pkg="git"; Cmd="git"},
    @{Name="Docker Engine"; Pkg="docker.io"; Cmd="docker"},
    @{Name="Docker Compose Plugin"; Pkg="docker-compose-plugin"; Cmd=$null},
    @{Name="Build Essential"; Pkg="build-essential"; Cmd="gcc"},
    @{Name="Python3 + venv/pip"; Pkg="python3 python3-venv python3-pip"; Cmd="python3"},
    @{Name="Vulkan Tools"; Pkg="vulkan-tools"; Cmd="vulkaninfo"},
    @{Name="Mesa Vulkan Drivers (RADV)"; Pkg="mesa-vulkan-drivers"; Cmd=$null},
    @{Name="FFmpeg"; Pkg="ffmpeg"; Cmd="ffmpeg"},
    @{Name="Tesseract OCR"; Pkg="tesseract-ocr"; Cmd="tesseract"},
    @{Name="NodeJS + npm"; Pkg="nodejs npm"; Cmd="node"},
    @{Name="lm-sensors"; Pkg="lm-sensors"; Cmd="sensors"},
    @{Name="pciutils"; Pkg="pciutils"; Cmd="lspci"},
    @{Name="VLC"; Pkg="vlc"; Cmd="vlc"},
    @{Name="Firefox"; Pkg="firefox"; Cmd="firefox"}
)

foreach ($pkg in $AptPackages) {
    $already = $false
    if ($pkg.Cmd) {
        $already = [bool](Get-Command $pkg.Cmd -ErrorAction SilentlyContinue)
    }
    if ($already) {
        Write-Host "[OK] $($pkg.Name) ja instalado." -ForegroundColor Green
    } else {
        Write-Host "[*] Instalando $($pkg.Name) ($($pkg.Pkg))..." -ForegroundColor Yellow
        $pkgList = $pkg.Pkg -split " "
        apt-get install -y @pkgList
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[!] apt-get retornou codigo $LASTEXITCODE para $($pkg.Name). Prosseguindo mesmo assim." -ForegroundColor DarkYellow
        }
    }
}

Write-Host "[*] Validando Python no PATH..." -ForegroundColor Cyan
$pythonCheck = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $pythonCheck) {
    Write-Host "[X] python3 nao encontrado mesmo apos instalacao via apt." -ForegroundColor Red
    exit 1
} else {
    Write-Host "[OK] Python encontrado em: $($pythonCheck.Source)" -ForegroundColor Green
    python3 --version
    # O resto do instalador (common.ps1) chama "python"/"pip" igual ao
    # Windows - cria alias na sessao atual pra nao duplicar logica.
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Set-Alias -Name python -Value python3 -Scope Global
    }
    if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
        Set-Alias -Name pip -Value pip3 -Scope Global
    }
}

if (-not (Test-Path "./api_server.py")) {
    Write-Host "[X] Arquivo api_server.py nao encontrado nesta pasta! O codigo fonte da Phoenix esta faltando." -ForegroundColor Red
    exit 1
}

# Dependencias Python EXCLUSIVAS do Linux para telemetria de hardware.
# De proposito NAO instalamos HardwareMonitor/wmi/pywin32 aqui - essas libs
# so existem no Windows e o import falharia. No Linux a leitura de sensores
# reais acontece via sysfs (/sys/class/drm, hwmon) e vulkaninfo/lspci.
Write-Host "`n=== DEPENDENCIAS PYTHON EXCLUSIVAS DO LINUX ===" -ForegroundColor Cyan
# Ubuntu 24.04+ marca o Python do sistema como "externally managed" (PEP 668)
# e bloqueia "pip install" direto (erro: externally-managed-environment).
# Como essas libs sao utilitarios de sistema (nao o venv da propria Phoenix,
# que common.ps1 cria depois), instalamos com --break-system-packages.
python3 -m pip install --upgrade pip --break-system-packages
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Falha ao atualizar o pip (codigo $LASTEXITCODE). Prosseguindo mesmo assim." -ForegroundColor DarkYellow
}
pip3 install pyudev --break-system-packages
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Falha ao instalar pyudev (codigo $LASTEXITCODE). Prosseguindo mesmo assim." -ForegroundColor DarkYellow
}

# Self-test de sensores de GPU via sysfs/DRM - equivalente Linux do
# self-test do LibreHardwareMonitor no Windows. Mesmos 3 checks: GPU
# detectada, sensor(es) legiveis, dados nao vazios.
Write-Host "`n=== SELF-TEST: SENSORES DE GPU (sysfs/DRM) ===" -ForegroundColor Cyan

$selfTestScript = @'
import glob
import os
import sys

gpu_found = False
sensor_found = False

for card in sorted(glob.glob("/sys/class/drm/card[0-9]*/device")):
    vendor_path = os.path.join(card, "vendor")
    if not os.path.exists(vendor_path):
        continue
    with open(vendor_path) as f:
        vendor = f.read().strip()
    # 0x1002 = AMD
    if vendor != "0x1002":
        continue

    gpu_found = True
    print(f"[i] GPU AMD detectada em: {card}")

    busy_path = os.path.join(card, "gpu_busy_percent")
    if os.path.exists(busy_path):
        with open(busy_path) as f:
            print(f"    - gpu_busy_percent = {f.read().strip()}")
        sensor_found = True

    vram_path = os.path.join(card, "mem_info_vram_used")
    if os.path.exists(vram_path):
        with open(vram_path) as f:
            print(f"    - mem_info_vram_used = {f.read().strip()} bytes")
        sensor_found = True

    hwmon_glob = os.path.join(card, "hwmon", "hwmon*", "temp1_input")
    for hwmon_path in glob.glob(hwmon_glob):
        with open(hwmon_path) as f:
            milli_c = int(f.read().strip())
        print(f"    - temp1_input = {milli_c / 1000:.1f} C")
        sensor_found = True

if not gpu_found:
    print("[X] Nenhuma GPU AMD foi detectada em /sys/class/drm.")
    sys.exit(1)
if not sensor_found:
    print("[X] GPU detectada mas sem sensores legiveis em sysfs.")
    print("    Verifique se o driver amdgpu esta carregado (lsmod | grep amdgpu).")
    sys.exit(1)

print("[OK] Sensores de GPU funcionando via sysfs.")
sys.exit(0)
'@

$selfTestPath = "/tmp/phoenix_gpu_selftest_linux.py"
Set-Content -Path $selfTestPath -Value $selfTestScript -Encoding UTF8

python3 $selfTestPath
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Self-test de sensores passou. A API deve abrir com sensores de GPU funcionando." -ForegroundColor Green
} else {
    Write-Host "[!] Self-test de sensores FALHOU (ver mensagens acima)." -ForegroundColor Red
    Write-Host "    A API ainda vai abrir, mas os campos de GPU (temp/load/VRAM) vao aparecer como 'INDISPONIVEL'." -ForegroundColor Yellow
    Write-Host "    Causa mais comum: driver amdgpu nao carregado ou usuario sem permissao de leitura em /sys." -ForegroundColor Yellow
}
Remove-Item $selfTestPath -ErrorAction SilentlyContinue

if ($Global:PhoenixBestDisk) {
    Write-Host "[i] storage_scanner.ps1 recomendou $($Global:PhoenixBestDisk.Path) ($($Global:PhoenixBestDisk.Kind)) para dados do Docker." -ForegroundColor DarkGray
    Write-Host "    Se quiser usar esse disco, configure 'data-root' em /etc/docker/daemon.json e reinicie o docker." -ForegroundColor DarkGray
}

# Garante que o Docker Engine (systemd) esta rodando - equivalente Linux
# do "abrir o Docker Desktop" no install/windows.ps1
Write-Host "`n=== DOCKER ENGINE ===" -ForegroundColor Cyan
& docker info 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Docker daemon ja estava ativo." -ForegroundColor Green
} else {
    Write-Host "[!] Docker daemon nao respondeu. Tentando iniciar via systemctl..." -ForegroundColor Yellow
    if (Get-Command systemctl -ErrorAction SilentlyContinue) {
        systemctl enable --now docker
    } else {
        Write-Host "[X] systemctl nao encontrado - nao foi possivel iniciar o Docker automaticamente." -ForegroundColor Red
        Write-Host "    Inicie manualmente com o gerenciador de servicos da sua distro." -ForegroundColor Red
        exit 1
    }

    $dockerReady = $false
    for ($i = 1; $i -le 20; $i++) {
        Start-Sleep -Seconds 2
        & docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            Write-Host "[OK] Docker daemon respondeu apos $($i * 2)s." -ForegroundColor Green
            break
        }
        Write-Host "    Aguardando... ($i/20)" -ForegroundColor DarkGray
    }

    if (-not $dockerReady) {
        Write-Host "[X] Docker daemon nao respondeu a tempo." -ForegroundColor Red
        Write-Host "    Verifique com: sudo systemctl status docker" -ForegroundColor Red
        Write-Host "    E se seu usuario esta no grupo docker: sudo usermod -aG docker `$USER (requer novo login)." -ForegroundColor Red
        exit 1
    }
}
