# install/linux.ps1
# Camada exclusiva do LINUX (Ubuntu/Debian)

 $currentUid = (id -u)
if ($currentUid -ne "0") {
    Write-Host "[X] Este instalador precisa rodar como root." -ForegroundColor Red
    Write-Host "    Rode novamente com: sudo pwsh ./install_phoenix.ps1" -ForegroundColor Yellow
    return @{ 
        Name="Linux"; Version="N/A"; Success=$false; ErrorCode="PX005"; 
        Warnings=@(); Errors=@("Root requerido"); RestartRequired=$false; Artifacts=@(); Timestamp=Get-Date 
    }
}

Write-Host "[OK] Executando como root em: $PWD" -ForegroundColor Green

if (-not (Get-Command apt-get -ErrorAction SilentlyContinue)) {
    return @{ 
        Name="Linux"; Version="N/A"; Success=$false; ErrorCode="PX006"; 
        Warnings=@(); Errors=@("apt-get nao encontrado"); RestartRequired=$false; Artifacts=@(); Timestamp=Get-Date 
    }
}

Write-Host "`n=== INSTALACAO DE PRE-REQUISITOS (APT) ===" -ForegroundColor Cyan
apt-get update -y 2>&1 | Out-Null

 $AptPackages = @(
    # CORREÇÃO ARQUITETURAL: Git foi movido pro install_phoenix.ps1 (bootstrap).
    @{Name="Docker Engine"; Pkg="docker.io"; Cmd="docker"},
    @{Name="Docker Compose Plugin"; Pkg="docker-compose-v2"; Cmd=$null},
    @{Name="Build Essential"; Pkg="build-essential"; Cmd="gcc"},
    @{Name="Python3 + venv/pip"; Pkg="python3 python3-venv python3-pip"; Cmd="python3"},
    @{Name="Vulkan Tools"; Pkg="vulkan-tools"; Cmd="vulkaninfo"},
    @{Name="Mesa Vulkan Drivers (RADV)"; Pkg="mesa-vulkan-drivers"; Cmd=$null},
    @{Name="CMake (Para compilar IA)"; Pkg="cmake"; Cmd="cmake"},
    @{Name="FFmpeg"; Pkg="ffmpeg"; Cmd="ffmpeg"},
    @{Name="Tesseract OCR"; Pkg="tesseract-ocr"; Cmd="tesseract"},
    @{Name="NodeJS + npm"; Pkg="nodejs npm"; Cmd="node"},
    @{Name="lm-sensors"; Pkg="lm-sensors"; Cmd="sensors"},
    @{Name="pciutils"; Pkg="pciutils"; Cmd="lspci"}
)

 $warnings = @()

foreach ($pkg in $AptPackages) {
    $already = $false
    if ($pkg.Cmd) { $already = [bool](Get-Command $pkg.Cmd -ErrorAction SilentlyContinue) }
    if ($already) {
        Write-Host "[OK] $($pkg.Name) ja instalado." -ForegroundColor Green
    } else {
        Write-Host "[*] Instalando $($pkg.Name)..." -ForegroundColor Yellow
        $pkgList = $pkg.Pkg -split " "
        apt-get install -y @pkgList 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { $warnings += "$($pkg.Name): apt retornou codigo $LASTEXITCODE" }
    }
}

# Garante que o comando 'python' aponta para 'python3' no Linux
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[*] Criando symlink python -> python3..." -ForegroundColor Yellow
    & ln -s /usr/bin/python3 /usr/bin/python 2>&1 | Out-Null
}
if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
    & ln -s /usr/bin/pip3 /usr/bin/pip 2>&1 | Out-Null
}

 $pythonCheck = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCheck) {
    return @{ 
        Name="Linux"; Version="N/A"; Success=$false; ErrorCode="PX007"; 
        Warnings=$warnings; Errors=@("python nao encontrado mesmo apos symlink"); RestartRequired=$false; Artifacts=@(); Timestamp=Get-Date 
    }
}

Write-Host "`n=== DOCKER ENGINE ===" -ForegroundColor Cyan
& docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    if (Get-Command systemctl -ErrorAction SilentlyContinue) {
        systemctl enable --now docker 2>&1 | Out-Null
    }
    $dockerReady = $false
    for ($i = 1; $i -le 20; $i++) {
        Start-Sleep -Seconds 2
        & docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { $dockerReady = $true; break }
    }
    if (-not $dockerReady) { $warnings += "Docker daemon nao respondeu" }
}

Write-Host "`n=== ATALHO DE APLICATIVO (MENU + AREA DE TRABALHO) ===" -ForegroundColor Cyan
try {
    $iconPath = Join-Path $PhoenixRoot "assets/phoenix_engine.png"
    $launcherPath = Join-Path $PhoenixRoot "Iniciar_Phoenix.sh"

    # CORREÇÃO CRÍTICA: o script inteiro roda como root (via sudo, exigido
    # no topo deste arquivo). $env:HOME aqui aponta pra "/root", NAO pra
    # pasta do usuario real - o atalho seria criado num lugar que o usuario
    # nunca ve. $env:SUDO_USER e setado automaticamente pelo sudo com o
    # nome do usuario original; resolvemos a home real dele via getent.
    $targetUser = $env:SUDO_USER
    $targetHome = $null

    if ($targetUser) {
        $passwdEntry = getent passwd $targetUser 2>$null
        if ($passwdEntry) {
            $targetHome = ($passwdEntry -split ":")[5]
        }
    }
    if (-not $targetHome) {
        # Nao rodou via sudo (ex: ja e root de verdade) - usa $env:HOME mesmo.
        $targetUser = $env:USER
        $targetHome = $env:HOME
        Write-Host "[!] SUDO_USER nao definido - usando HOME atual ($targetHome). Se isso nao for a pasta do usuario certo, o atalho pode nao aparecer." -ForegroundColor Yellow
    }

    if ((Test-Path $iconPath) -and (Test-Path $launcherPath) -and $targetHome -and (Test-Path $targetHome)) {
        chmod +x $launcherPath 2>&1 | Out-Null

        $desktopEntry = @"
[Desktop Entry]
Type=Application
Name=Phoenix Engine
Comment=Hardware nao morre - so espera o software certo.
Exec=$launcherPath
Icon=$iconPath
Terminal=true
Categories=Development;Utility;
"@

        $createdPaths = @()

        # Menu de aplicativos (aparece na busca do GNOME/KDE etc.)
        $appsDir = Join-Path $targetHome ".local/share/applications"
        if (-not (Test-Path $appsDir)) { New-Item -ItemType Directory -Force -Path $appsDir | Out-Null }
        $appsEntryPath = Join-Path $appsDir "phoenix-engine.desktop"
        Set-Content -Path $appsEntryPath -Value $desktopEntry -Encoding UTF8
        chmod +x $appsEntryPath 2>&1 | Out-Null
        $createdPaths += $appsEntryPath

        # Area de Trabalho - roda xdg-user-dir COMO O USUARIO REAL (via
        # "su -l"), pra respeitar o nome localizado da pasta (ex: "Área de
        # Trabalho" em PT-BR) - rodando como root, xdg-user-dir nao teria
        # o contexto/config correto do usuario.
        $desktopDir = $null
        if (Get-Command xdg-user-dir -ErrorAction SilentlyContinue) {
            $xdgDesktop = (su -l $targetUser -c "xdg-user-dir DESKTOP" 2>$null).Trim()
            if ($xdgDesktop -and (Test-Path $xdgDesktop)) { $desktopDir = $xdgDesktop }
        }
        if (-not $desktopDir) {
            $fallback = Join-Path $targetHome "Desktop"
            if (Test-Path $fallback) { $desktopDir = $fallback }
        }

        if ($desktopDir) {
            $desktopEntryPath = Join-Path $desktopDir "phoenix-engine.desktop"
            Set-Content -Path $desktopEntryPath -Value $desktopEntry -Encoding UTF8
            chmod +x $desktopEntryPath 2>&1 | Out-Null
            $createdPaths += $desktopEntryPath
            # Sem isso o GNOME mostra "Launcher nao confiavel" e exige
            # clique manual em "Confiar e Iniciar" na primeira vez.
            if (Get-Command gio -ErrorAction SilentlyContinue) {
                gio set $desktopEntryPath "metadata::trusted" true 2>&1 | Out-Null
            }
        }

        # Como tudo foi criado como root, devolve a posse pro usuario real -
        # senao ele nem consegue apagar/editar o proprio atalho depois.
        foreach ($p in $createdPaths) {
            chown "${targetUser}:${targetUser}" $p 2>&1 | Out-Null
        }

        if (Get-Command update-desktop-database -ErrorAction SilentlyContinue) {
            update-desktop-database $appsDir 2>&1 | Out-Null
        }

        $suffix = if ($desktopDir) { " e na Area de Trabalho" } else { "" }
        Write-Host "[OK] Atalho criado no menu de aplicativos$suffix (usuario: $targetUser)." -ForegroundColor Green
    } else {
        Write-Host "[!] assets/phoenix_engine.png, Iniciar_Phoenix.sh ou pasta do usuario nao encontrados - atalho nao criado." -ForegroundColor Yellow
        $warnings += "Atalho de aplicativo nao criado (icone, launcher ou home do usuario ausente)."
    }
} catch {
    Write-Host "[!] Falha ao criar atalho: $($_.Exception.Message)" -ForegroundColor Yellow
    $warnings += "Falha ao criar atalho de aplicativo: $($_.Exception.Message)"
}

# Contrato de Retorno Estrito
return @{
    Name = "Linux"
    Version = "1.0.0"
    Success = $true
    ErrorCode = ""
    Warnings = $warnings
    Errors = @()
    RestartRequired = $false
    Artifacts = @("python3", "git", "docker", "node", "cmake")
    Timestamp = Get-Date
}