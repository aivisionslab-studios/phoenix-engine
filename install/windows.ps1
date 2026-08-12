# install/windows.ps1
# Camada especifica do WINDOWS (10 e 11).

# =====================================================================
# 1. INICIALIZACAO
# =====================================================================

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host " PHOENIX WINDOWS PROVISIONING" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

 $warnings = @()
 $restartRequired = $false

 $PhoenixPorts = @(3000, 8000, 8080, 8081, 8088, 11434, 7860, 8010)

# =====================================================================
# 2. FUNCOES AUXILIARES
# =====================================================================

function New-FailContract {
    param([string]$ErrMsg, [string]$Code, [array]$Warnings = @())
    return @{
        Name = "Windows"; Version = "N/A"; Success = $false; ErrorCode = $Code
        Warnings = $Warnings; Errors = @($ErrMsg); RestartRequired = $false
        Artifacts = @(); Timestamp = Get-Date
    }
}

function Write-Step {
    param([string]$Text, [string]$Color = "Cyan")
    Write-Host "`n=== $Text ===" -ForegroundColor $Color
}

function Test-Command {
    param([Parameter(Mandatory)] [string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Add-MachinePath {
    param([Parameter(Mandatory)] [string]$Dir)
    if (-not (Test-Path $Dir)) { return }
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($machinePath -notlike "*$Dir*") {
        [System.Environment]::SetEnvironmentVariable("Path", "$machinePath;$Dir", "Machine")
        Write-Host "[*] PATH de maquina atualizado com: $Dir" -ForegroundColor DarkGray
    }
}

function Refresh-SessionPath {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Install-WingetPackage {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [string]$Id,
        [string]$Command = $null,
        [scriptblock]$Validation = $null,
        [switch]$Required,
        [switch]$RestartAfter,
        [string[]]$ExtraArgs = @()
    )

    $alreadyPresent = $false
    if ($Validation) {
        $alreadyPresent = [bool](& $Validation)
    } elseif ($Command) {
        $alreadyPresent = Test-Command $Command
    }

    if ($alreadyPresent) {
        Write-Host "[OK] $Name ja instalado." -ForegroundColor Green
        return @{ Installed = $false; AlreadyPresent = $true; Warning = $null; RestartNeeded = $false; Fatal = $false }
    }

    Write-Host "[*] Instalando $Name..." -ForegroundColor Yellow
    $argList = @("install", "-e", "--id", $Id, "--accept-package-agreements", "--accept-source-agreements") + $ExtraArgs
    & winget @argList 2>&1 | Out-Null

    $warning = $null
    $fatal = $false
    if ($LASTEXITCODE -ne 0) {
        $warning = "$Name`: winget retornou codigo $LASTEXITCODE"
        if ($Required) { $fatal = $true }
    }

    return @{
        Installed = $true
        AlreadyPresent = $false
        Warning = $warning
        RestartNeeded = [bool]$RestartAfter
        Fatal = $fatal
    }
}

function Install-TesseractWithFallback {
    if (Test-Command "tesseract") {
        Write-Host "[OK] Tesseract OCR ja instalado." -ForegroundColor Green
        return @{ Installed = $false; AlreadyPresent = $true; Warning = $null; RestartNeeded = $false; Fatal = $false }
    }

    Write-Host "[*] Tentando instalar Tesseract via winget..." -ForegroundColor Yellow
    $result = Install-WingetPackage -Name "Tesseract OCR" -Id "UB-Mannheim.TesseractOCR" -Command "tesseract"

    if (-not $result.Warning -and (Test-Command "tesseract")) {
        return $result
    }

    Write-Host "[!] Winget falhou para Tesseract. Baixando instalador diretamente do GitHub..." -ForegroundColor Yellow
    $tesseractUrl = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
    $tesseractInstaller = Join-Path $env:TEMP "tesseract-setup.exe"
    $tesseractInstalled = $false

    try {
        Invoke-WebRequest -Uri $tesseractUrl -OutFile $tesseractInstaller -UseBasicParsing
        Start-Process -FilePath $tesseractInstaller -ArgumentList "/S /D=C:\Program Files\Tesseract-OCR" -Wait -NoNewWindow
        Remove-Item $tesseractInstaller -Force -ErrorAction SilentlyContinue

        Add-MachinePath -Dir "C:\Program Files\Tesseract-OCR"
        Refresh-SessionPath

        if (Test-Command "tesseract") {
            $tesseractInstalled = $true
            Write-Host "[OK] Tesseract OCR instalado via download direto." -ForegroundColor Green
        }
    } catch {
        Write-Host "[X] Falha ao baixar Tesseract: $($_.Exception.Message)" -ForegroundColor Red
    }

    if ($tesseractInstalled) {
        return @{ Installed = $true; AlreadyPresent = $false; Warning = $null; RestartNeeded = $false; Fatal = $false }
    }

    return @{
        Installed = $false
        AlreadyPresent = $false
        Warning = "Tesseract OCR nao pode ser instalado automaticamente (winget e download direto falharam)."
        RestartNeeded = $false
        Fatal = $false
    }
}

function Test-WindowsFeatureEnabled {
    param([string]$FeatureName)
    try {
        $feature = Get-WindowsOptionalFeature -Online -FeatureName $FeatureName -ErrorAction Stop
        return ($feature.State -eq "Enabled")
    } catch {
        return $false
    }
}

function Enable-WindowsFeatureSafe {
    param([string]$FeatureName, [string]$DisplayName)
    if (Test-WindowsFeatureEnabled -FeatureName $FeatureName) {
        Write-Host "[OK] $DisplayName ja habilitado." -ForegroundColor Green
        return $false
    }
    Write-Host "[*] Habilitando $DisplayName..." -ForegroundColor Yellow
    try {
        Enable-WindowsOptionalFeature -Online -FeatureName $FeatureName -All -NoRestart -ErrorAction Stop | Out-Null
        Write-Host "[OK] $DisplayName habilitado (reinicio necessario pra efetivar)." -ForegroundColor Yellow
        return $true
    } catch {
        Write-Host "[!] Falha ao habilitar $DisplayName`: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Start-DockerDesktop {
    param([int]$MaxAttempts = 40, [int]$IntervalSeconds = 3)

    & docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { return $true }

    $dockerExePaths = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe"
    )
    $dockerExe = $dockerExePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $dockerExe) { return $false }

    Start-Process -FilePath $dockerExe | Out-Null
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        Start-Sleep -Seconds $IntervalSeconds
        & docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { return $true }
    }
    return $false
}

function Test-HardwareMonitorLibrary {
    $script = @'
import sys
try:
    import clr
except ImportError:
    sys.exit(1)
try:
    from HardwareMonitor.Hardware import Computer
except Exception:
    sys.exit(1)
sys.exit(0)
'@
    $path = Join-Path $env:TEMP "phx_hwmon_check.py"
    Set-Content -Path $path -Value $script -Encoding UTF8
    & python $path 2>&1 | Out-Null
    $ok = ($LASTEXITCODE -eq 0)
    Remove-Item $path -ErrorAction SilentlyContinue
    return $ok
}

function Test-GpuSensors {
    $script = @'
import sys
try:
    import clr
    from HardwareMonitor.Hardware import Computer
    computer = Computer()
    computer.IsGpuEnabled = True
    computer.Open()
except Exception:
    sys.exit(1)
gpu_found = False
sensor_found = False
for hw in computer.Hardware:
    hw.Update()
    if "Gpu" in str(hw.HardwareType):
        gpu_found = True
        if list(hw.Sensors):
            sensor_found = True
sys.exit(0 if (gpu_found and sensor_found) else 1)
'@
    $path = Join-Path $env:TEMP "phx_gpu_check.py"
    Set-Content -Path $path -Value $script -Encoding UTF8
    & python $path 2>&1 | Out-Null
    $ok = ($LASTEXITCODE -eq 0)
    Remove-Item $path -ErrorAction SilentlyContinue
    return $ok
}

function Test-VulkanRuntime {
    if (-not (Test-Command "vulkaninfo")) { return $false }
    & vulkaninfo --summary 2>&1 | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Invoke-SelfTest {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [scriptblock]$Test
    )
    Write-Host "[*] Self-test: $Name..." -ForegroundColor Cyan
    try {
        $result = [bool](& $Test)
    } catch {
        Write-Host "[!] $Name falhou com excecao: $($_.Exception.Message)" -ForegroundColor Yellow
        return $false
    }

    if ($result) {
        Write-Host "[OK] $Name passou." -ForegroundColor Green
    } else {
        Write-Host "[!] $Name falhou." -ForegroundColor Yellow
    }
    return $result
}

# =====================================================================
# 3. VERIFICACAO DE PRIVILEGIOS
# =====================================================================

if (-not (Test-IsAdministrator)) {
    Write-Host "[X] Este instalador precisa rodar como Administrador." -ForegroundColor Red
    Write-Host "    Feche o terminal e abra novamente com 'Executar como administrador'." -ForegroundColor Yellow
    return (New-FailContract "Privilegios de administrador necessarios" "PX008")
}
Write-Host "[OK] Executando como Administrador." -ForegroundColor Green

# =====================================================================
# 4. WINGET
# =====================================================================

if (-not (Test-Command "winget")) {
    Write-Host "[X] Winget nao encontrado." -ForegroundColor Red
    return (New-FailContract "Winget nao encontrado" "PX003")
}

Write-Host "[*] Atualizando fontes do winget..." -ForegroundColor DarkGray
& winget source update 2>&1 | Out-Null

# =====================================================================
# 5. PYTHON
# =====================================================================

Write-Step "INSTALACAO/REPARO DO PYTHON 3.12"

Write-Host "[*] Reinstalando/Reparando Python 3.12..." -ForegroundColor Yellow
& winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --force --scope machine --silent --override "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_launcher=1" 2>&1 | Out-Null

foreach ($root in @("C:\Program Files\Python312", "C:\Program Files\Python312\Scripts")) {
    Add-MachinePath -Dir $root
}

# =====================================================================
# 6. PATH
# =====================================================================

Refresh-SessionPath

Write-Host "[*] Validando Python no PATH da sessao atual..." -ForegroundColor Cyan
 $pythonCheck = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCheck) {
    return (New-FailContract "Python nao encontrado no PATH" "PX004" $warnings)
}
Write-Host "[OK] Python encontrado em: $($pythonCheck.Source)" -ForegroundColor Green

# =====================================================================
# 7. INSTALACAO DOS COMPONENTES (categorizada)
# =====================================================================

 $PackageCategories = [ordered]@{
    "CORE" = @(
        @{Name="Docker Desktop";  Id="Docker.DockerDesktop";      Cmd="docker";  RestartAfter=$true; Required=$true}
        @{Name="PowerShell";      Id="Microsoft.PowerShell";      Cmd="pwsh"}
        @{Name=".NET SDK 9.0";    Id="Microsoft.DotNet.SDK.9";    Cmd="dotnet"}
        @{Name="NodeJS LTS";      Id="OpenJS.NodeJS.LTS";         Cmd="node"}
    )
    "BUILD" = @(
        @{Name="Visual Studio Build Tools"; Id="Microsoft.VisualStudio.2022.BuildTools"; Cmd="vswhere"}
        @{Name="Vulkan SDK";                Id="KhronosGroup.VulkanSDK";                 Cmd="vulkaninfo"}
    )
    "AI" = @(
        @{Name="LM Studio"; Id="ElementLabs.LMStudio"; Cmd="lms"}
    )
    "UTILITIES" = @(
        @{Name="FFmpeg";          Id="Gyan.FFmpeg";              Cmd="ffmpeg"}
        @{Name="PowerToys";       Id="Microsoft.PowerToys";      Cmd="powertoys"}
        @{Name="GitHub Desktop";  Id="GitHub.GitHubDesktop";     Cmd="github"}
        @{Name="VLC";             Id="VideoLAN.VLC";             Cmd="vlc"}
        @{Name="Firefox";         Id="Mozilla.Firefox";          Cmd="firefox"}
        @{Name="Chrome";          Id="Google.Chrome";            Cmd="chrome"}
    )
}

foreach ($category in $PackageCategories.Keys) {
    Write-Host "`n========== $category ==========" -ForegroundColor Magenta
    foreach ($pkg in $PackageCategories[$category]) {
        Write-Host "[*] Verificando $($pkg.Name)..."
        $result = Install-WingetPackage -Name $pkg.Name -Id $pkg.Id -Command $pkg.Cmd `
            -Required:($pkg.Required -eq $true) -RestartAfter:($pkg.RestartAfter -eq $true)

        if ($result.Fatal) {
            return (New-FailContract "$($pkg.Name) e obrigatorio e a instalacao falhou (winget)" "PX009" $warnings)
        }
        if ($result.Warning) { $warnings += $result.Warning }
        if ($result.RestartNeeded -and $result.Installed) { $restartRequired = $true }
    }
}

# TESSERACT OCR - instalacao com fallback de download direto
Write-Host "`n========== UTILITIES (Tesseract) ==========" -ForegroundColor Magenta
Write-Host "[*] Verificando Tesseract OCR..."
 $tesseractResult = Install-TesseractWithFallback
if ($tesseractResult.Warning) { $warnings += $tesseractResult.Warning }

if (-not (Test-Command "lms")) {
    Write-Host "[!] AVISO: LM Studio foi instalado, mas a CLI 'lms' nao foi encontrada no PATH." -ForegroundColor Yellow
    Write-Host "    Para habilitar a automacao da Phoenix, abra o LM Studio manualmente uma vez," -ForegroundColor Yellow
    Write-Host "    feche-o em seguida, e reinicie o terminal/Phoenix." -ForegroundColor Yellow
    $warnings += "LM Studio CLI (lms) nao inicializada. Abra o app uma vez."
}

# =====================================================================
# 8. CONFIGURACAO DO WINDOWS
# =====================================================================

Write-Step "CONFIGURACAO DO WINDOWS"

if (Enable-WindowsFeatureSafe -FeatureName "Microsoft-Windows-Subsystem-Linux" -DisplayName "WSL") { $restartRequired = $true }
if (Enable-WindowsFeatureSafe -FeatureName "VirtualMachinePlatform" -DisplayName "Virtual Machine Platform (WSL2)") { $restartRequired = $true }

if (-not (Test-WindowsFeatureEnabled -FeatureName "Microsoft-Hyper-V-All")) {
    $warnings += "Hyper-V nao habilitado (opcional - Docker Desktop usa WSL2 por padrao)."
}

 $virtEnabled = (Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue).VirtualizationFirmwareEnabled
if ($virtEnabled -eq $false) {
    $warnings += "Virtualizacao (VT-x/AMD-V) parece desabilitada na BIOS/UEFI. Docker e WSL2 nao funcionam sem isso."
} else {
    Write-Host "[OK] Virtualizacao habilitada na BIOS/UEFI." -ForegroundColor Green
}

try {
    $avx2Supported = [System.Runtime.Intrinsics.X86.Avx2]::IsSupported
} catch {
    $avx2Supported = $null
}
if ($avx2Supported -eq $false) {
    $warnings += "CPU sem suporte a AVX2 - builds do llama.cpp podem cair pra um caminho mais lento."
} elseif ($avx2Supported -eq $true) {
    Write-Host "[OK] CPU com suporte a AVX2." -ForegroundColor Green
}

foreach ($port in $PhoenixPorts) {
    $ruleName = "Phoenix Engine - Porta $port"
    if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
        try {
            New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow | Out-Null
        } catch {
            $warnings += "Nao foi possivel criar regra de firewall pra porta $port`: $($_.Exception.Message)"
        }
    }
}
Write-Host "[OK] Firewall liberado para as portas da Phoenix ($($PhoenixPorts -join ', '))." -ForegroundColor Green

try {
    $devModeKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"
    if (-not (Test-Path $devModeKey)) { New-Item -Path $devModeKey -Force | Out-Null }
    Set-ItemProperty -Path $devModeKey -Name "AllowDevelopmentWithoutDevLicense" -Value 1 -Type DWord -Force
    Write-Host "[OK] Developer Mode habilitado." -ForegroundColor Green
} catch {
    $warnings += "Nao foi possivel habilitar o Developer Mode: $($_.Exception.Message)"
}

try {
    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -Type DWord -Force
    Write-Host "[OK] Long Paths habilitado." -ForegroundColor Green
} catch {
    $warnings += "Nao foi possivel habilitar Long Paths: $($_.Exception.Message)"
}

try {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine -Force
    Write-Host "[OK] Execution Policy ajustada para RemoteSigned (LocalMachine)." -ForegroundColor Green
} catch {
    $warnings += "Nao foi possivel ajustar a Execution Policy em Scope LocalMachine: $($_.Exception.Message)"
    try {
        Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
        Write-Host "[!] Fallback: Execution Policy ajustada para Bypass (Scope Process, so nesta sessao)." -ForegroundColor Yellow
    } catch {
        $warnings += "Fallback de Execution Policy (Scope Process) tambem falhou: $($_.Exception.Message)"
    }
}

try {
    $iconPath = Join-Path $PhoenixRoot "assets\phoenix_engine.ico"
    $launcherPath = Join-Path $PhoenixRoot "Iniciar_Phoenix.bat"

    if ((Test-Path $iconPath) -and (Test-Path $launcherPath)) {
        $wsh = New-Object -ComObject WScript.Shell

        $desktopShortcut = Join-Path ([System.Environment]::GetFolderPath('Desktop')) "Phoenix Engine.lnk"
        $startMenuShortcut = Join-Path ([System.Environment]::GetFolderPath('Programs')) "Phoenix Engine.lnk"

        foreach ($shortcutPath in @($desktopShortcut, $startMenuShortcut)) {
            $shortcut = $wsh.CreateShortcut($shortcutPath)
            $shortcut.TargetPath = $launcherPath
            $shortcut.WorkingDirectory = $PhoenixRoot
            $shortcut.IconLocation = $iconPath
            $shortcut.Description = "Phoenix Engine - Hardware nao morre, so espera o software certo."
            $shortcut.Save()
        }
        Write-Host "[OK] Atalhos criados na Area de Trabalho e no Menu Iniciar." -ForegroundColor Green
    } else {
        Write-Host "[!] assets\phoenix_engine.ico ou Iniciar_Phoenix.bat nao encontrado - atalhos nao criados." -ForegroundColor Yellow
        $warnings += "Atalhos de Desktop/Menu Iniciar nao criados (icone ou launcher ausente)."
    }
} catch {
    Write-Host "[!] Falha ao criar atalhos: $($_.Exception.Message)" -ForegroundColor Yellow
    $warnings += "Falha ao criar atalhos de Desktop/Menu Iniciar: $($_.Exception.Message)"
}

# =====================================================================
# 8.5 VERIFICACAO DE REBOOT (Docker/WSL exigem reinicio)
# =====================================================================

if ($restartRequired) {
    Write-Host ""
    Write-Host "[!] REINICIO DO SISTEMA NECESSARIO" -ForegroundColor Yellow
    Write-Host "    O Windows acabou de instalar o Docker Desktop ou habilitar o WSL2." -ForegroundColor Yellow
    Write-Host "    Para que o Docker funcione corretamente, o sistema precisa ser reiniciado." -ForegroundColor Yellow
    Write-Host "    Por favor, reinicie o PC e rode o instalador novamente para continuar." -ForegroundColor Yellow
    return @{
        Name = "Windows"
        Version = "3.0.1"
        Success = $true
        ErrorCode = "REBOOT_REQUIRED"
        Warnings = $warnings
        Errors = @()
        RestartRequired = $true
        Artifacts = @()
        Timestamp = Get-Date
    }
}

# =====================================================================
# 9. DEPENDENCIAS PYTHON ESPECIFICAS DO WINDOWS
# =====================================================================

Write-Step "DEPENDENCIAS PYTHON ESPECIFICAS DO WINDOWS"

# PHX-FIX: Relaxa temporariamente o ErrorActionPreference para evitar que avisos do pip
# no stderr quebrem o script no PowerShell 5.1.
 $oldEAP = $ErrorActionPreference
 $ErrorActionPreference = "Continue"
try {
    & python -m pip install --upgrade pip 2>&1 | Out-Null
    & python -m pip install pythonnet HardwareMonitor wmi pywin32 --prefer-binary 2>&1 | Out-Host
} catch {
    Write-Host "[!] Aviso benigno durante a instalacao do pythonnet/HardwareMonitor: $($_.Exception.Message)" -ForegroundColor Yellow
}
 $ErrorActionPreference = $oldEAP

# =====================================================================
# 10. SELF-TESTS
# =====================================================================

Write-Step "SELF-TESTS"

 $SelfTests = [ordered]@{
    "Python"          = { (Test-Command "python") -and ((& python --version 2>&1) -match "Python") }
    "Docker"          = { Start-DockerDesktop }
    "HardwareMonitor" = { Test-HardwareMonitorLibrary }
    "GPU Sensors"     = { Test-GpuSensors }
    "Vulkan"          = { Test-VulkanRuntime }
    "LM Studio CLI"   = { Test-Command "lms" }
}

foreach ($testName in $SelfTests.Keys) {
    if (-not (Invoke-SelfTest -Name $testName -Test $SelfTests[$testName])) {
        $warnings += "Self-test '$testName' falhou"
    }
}

# =====================================================================
# 11. CONTRATO DE RETORNO
# =====================================================================

return @{
    Name = "Windows"
    Version = "3.0.1"
    Success = $true
    ErrorCode = ""
    Warnings = $warnings
    Errors = @()
    RestartRequired = $false
    Artifacts = @("python", "docker", "node", "lms")
    Timestamp = Get-Date
}