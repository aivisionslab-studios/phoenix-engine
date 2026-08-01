# install/windows.ps1
# Camada especifica do WINDOWS (10 e 11).
#
# Estrutura (arquitetura combinada com o ChatGPT):
#   1. Inicializacao
#   2. Funcoes auxiliares
#   3. Verificacao de privilegios
#   4. Winget
#   5. Python
#   6. PATH
#   7. Instalacao dos componentes (categorizada: CORE / BUILD / AI / UTILITIES)
#   8. Configuracao do Windows (WSL, Hyper-V, virtualizacao, AVX2, firewall,
#      Developer Mode, Long Paths, Execution Policy)
#   9. Dependencias Python especificas do Windows
#  10. Self-tests (Python, Docker, HardwareMonitor, GPU, Vulkan, LM Studio CLI)
#  11. Contrato de retorno
#
# NOTA: Git NAO aparece aqui. Git e responsabilidade do bootstrap
# (install_phoenix.ps1) - decisao arquitetural pra common.ps1 sempre
# poder assumir que git ja existe.

# =====================================================================
# 1. INICIALIZACAO
# =====================================================================

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host " PHOENIX WINDOWS PROVISIONING" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

 $warnings = @()
 $restartRequired = $false

# Portas oficiais da Phoenix (mesmo mapa do common.ps1 - nao alterar sem sincronizar)
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
    <#
        Instala um pacote via winget se a validacao de presenca falhar.
        - Command: nome de um executavel a checar com Get-Command (uso simples)
        - Validation: scriptblock customizado, tem prioridade sobre Command
        - Required: se a instalacao falhar, isso vira um erro fatal (Fatal=$true)
          em vez de só um warning
        - RestartAfter: sinaliza que esse pacote costuma exigir reinicio/relogin
        Retorna um hashtable simples - quem chama decide o que fazer.
    #>
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
    # Só confirma que a biblioteca CARREGA - nao mexe com GPU nenhuma aqui.
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
    # Confirma que existe hardware GPU detectado E que ele expõe sensores.
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
    <#
        Runner generico de self-test: recebe um nome e um scriptblock que
        retorna $true/$false. Centraliza o log e o tratamento de excecao,
        pra cada teste individual nao precisar repetir try/catch.
    #>
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
# NOTA: "Git" nao aparece em nenhuma categoria - e responsabilidade do
# bootstrap (install_phoenix.ps1), nao do windows.ps1.
# "Required=$true" = se a instalacao falhar, o provisionamento para (fatal).
# Sem "Required" = falha vira só warning e o instalador segue.

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
        @{Name="Tesseract OCR";   Id="UB-Mannheim.TesseractOCR"; Cmd="tesseract"}
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

# AVISO INTELIGENTE DO LM STUDIO
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

# --- WSL2 (backend padrao do Docker Desktop) ---
if (Enable-WindowsFeatureSafe -FeatureName "Microsoft-Windows-Subsystem-Linux" -DisplayName "WSL") { $restartRequired = $true }
if (Enable-WindowsFeatureSafe -FeatureName "VirtualMachinePlatform" -DisplayName "Virtual Machine Platform (WSL2)") { $restartRequired = $true }

# --- Hyper-V (opcional - só relevante se Docker Desktop usar esse backend em vez de WSL2) ---
if (-not (Test-WindowsFeatureEnabled -FeatureName "Microsoft-Hyper-V-All")) {
    $warnings += "Hyper-V nao habilitado (opcional - Docker Desktop usa WSL2 por padrao)."
}

# --- Virtualizacao habilitada na BIOS/UEFI (VT-x/AMD-V) ---
$virtEnabled = (Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue).VirtualizationFirmwareEnabled
if ($virtEnabled -eq $false) {
    $warnings += "Virtualizacao (VT-x/AMD-V) parece desabilitada na BIOS/UEFI. Docker e WSL2 nao funcionam sem isso."
} else {
    Write-Host "[OK] Virtualizacao habilitada na BIOS/UEFI." -ForegroundColor Green
}

# --- AVX2 (necessario para builds otimizados do llama.cpp) ---
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

# --- Firewall: libera as portas oficiais da Phoenix ---
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

# --- Developer Mode (opcional - facilita symlinks/compilacao sem elevar toda vez) ---
try {
    $devModeKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"
    if (-not (Test-Path $devModeKey)) { New-Item -Path $devModeKey -Force | Out-Null }
    Set-ItemProperty -Path $devModeKey -Name "AllowDevelopmentWithoutDevLicense" -Value 1 -Type DWord -Force
    Write-Host "[OK] Developer Mode habilitado." -ForegroundColor Green
} catch {
    $warnings += "Nao foi possivel habilitar o Developer Mode: $($_.Exception.Message)"
}

# --- Long Paths (necessario pra clonar 40+ repos com caminhos profundos, ex: node_modules) ---
try {
    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -Type DWord -Force
    Write-Host "[OK] Long Paths habilitado." -ForegroundColor Green
} catch {
    $warnings += "Nao foi possivel habilitar Long Paths: $($_.Exception.Message)"
}

# --- Execution Policy (garante que os proximos scripts da Phoenix rodem sem bloqueio) ---
try {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine -Force
    Write-Host "[OK] Execution Policy ajustada para RemoteSigned (LocalMachine)." -ForegroundColor Green
} catch {
    $warnings += "Nao foi possivel ajustar a Execution Policy: $($_.Exception.Message)"
}

# --- Atalhos na Area de Trabalho e no Menu Iniciar ---
# Usa GetFolderPath() em vez de caminho fixo tipo "C:\Users\<nome>\Desktop" -
# funciona pra qualquer usuario/perfil, inclusive OneDrive redirecionado.
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
# 9. DEPENDENCIAS PYTHON ESPECIFICAS DO WINDOWS
# =====================================================================

Write-Step "DEPENDENCIAS PYTHON ESPECIFICAS DO WINDOWS"
& python -m pip install pythonnet HardwareMonitor wmi pywin32 2>&1 | Out-Null

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
    Version = "3.0.0"
    Success = $true
    ErrorCode = ""
    Warnings = $warnings
    Errors = @()
    RestartRequired = $restartRequired
    Artifacts = @("python", "docker", "node", "lms")
    Timestamp = Get-Date
}
