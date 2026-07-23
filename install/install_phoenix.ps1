# install_phoenix.ps1
# Bootstrapper Oficial da Phoenix Engine 5.0

# 1. COMPATIBILIDADE E DETECCAO DE SO (A prova de WSL2)
if ($PSVersionTable.PSEdition -eq 'Desktop' -or $PSVersionTable.PSVersion.Major -lt 6) {
    $IsWindows = $true
    $IsLinux = $false
    $IsMacOS = $false
} else {
    # No PowerShell 7+, garante que não confunde WSL com Linux nativo
    if ([System.Environment]::OSVersion.Platform -eq 'Win32NT') {
        $IsWindows = $true
        $IsLinux = $false
    }
}

# 2. AUTO-ELEVAÇÃO PARA ADMINISTRADOR (Apenas Windows)
if ($IsWindows) {
    $currentUser = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "[!] Solicitando privilegios de administrador..." -ForegroundColor Yellow

        # $PSCommandPath pode vir vazio dependendo de como o .ps1 foi
        # disparado (ex: duplo-clique via associacao de arquivo em vez de
        # "Run with PowerShell"). Sem isso, o Start-Process abaixo relança
        # o PowerShell SEM nenhum script pra rodar - ele abre e fecha na
        # hora, o que parece "nao fez nada". $MyInvocation.MyCommand.Path
        # e um fallback mais confiavel nesses casos.
        $scriptPath = $PSCommandPath
        if ([string]::IsNullOrEmpty($scriptPath)) {
            $scriptPath = $MyInvocation.MyCommand.Path
        }

        if ([string]::IsNullOrEmpty($scriptPath)) {
            Write-Host "[X] Nao foi possivel determinar o caminho deste script (PSCommandPath vazio)." -ForegroundColor Red
            Write-Host "    Rode o instalador assim, de dentro de um PowerShell ja aberto:" -ForegroundColor Red
            Write-Host "    cd `"caminho\da\pasta\do\projeto`"; .\install_phoenix.ps1" -ForegroundColor Yellow
            if (Get-Command Pause -ErrorAction SilentlyContinue) { Pause }
            exit 1
        }

        try {
            Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" -Verb RunAs -ErrorAction Stop
        } catch {
            # Acontece se o usuario clicar "Nao"/cancelar no prompt do UAC,
            # ou se a elevacao for bloqueada por politica de grupo. Sem este
            # catch, a excecao mata o processo aqui mesmo - janela fecha na
            # hora, sem nenhuma mensagem visivel.
            Write-Host "[X] A elevacao para Administrador foi cancelada ou bloqueada." -ForegroundColor Red
            Write-Host "    Detalhe: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "    Sem privilegios de administrador este instalador nao pode continuar." -ForegroundColor Red
            if (Get-Command Pause -ErrorAction SilentlyContinue) { Pause }
            exit 1
        }

        Stop-Process -Id $PID -Force
    }
}

 $ErrorActionPreference = "Continue"
 $ProgressPreference = "SilentlyContinue"
 $env:GIT_TERMINAL_PROMPT = "0"

 $PhoenixRoot = $PSScriptRoot
 $InstallDir = Join-Path $PhoenixRoot "install"
 Set-Location $PhoenixRoot

try {
    # 3. RODA O SCANNER DE ARMAZENAMENTO PRIMEIRO
    $scannerScript = Join-Path $InstallDir "storage_scanner.ps1"
    if (Test-Path $scannerScript) {
        . $scannerScript
    } else {
        Write-Host "[!] Scanner de armazenamento nao encontrado em $scannerScript. Pulando." -ForegroundColor Yellow
    }

    # 4. RODA A CAMADA ESPECIFICA DO SO
    if ($IsWindows) {
        Write-Host "[*] Sistema detectado: Windows" -ForegroundColor Cyan
        $osScript = Join-Path $InstallDir "windows.ps1"
    }
    elseif ($IsLinux) {
        Write-Host "[*] Sistema detectado: Linux" -ForegroundColor Cyan
        $osScript = Join-Path $InstallDir "linux.ps1"
    }
    else {
        throw "Sistema operacional nao suportado."
    }

    if (Test-Path $osScript) {
        . $osScript
    } else {
        throw "Arquivo nao encontrado: $osScript. Verifique se a pasta 'install/' e os scripts existem."
    }

    # 5. RODA A CAMADA COMUM (Python, Docker, Git, API)
    $commonScript = Join-Path $InstallDir "common.ps1"
    if (Test-Path $commonScript) {
        . $commonScript
    } else {
        throw "Arquivo nao encontrado: $commonScript. Verifique se a pasta 'install/' e os scripts existem."
    }
}
catch {
    Write-Host "`n[X] ERRO FATAL DURANTE O PROVISIONAMENTO:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "`nLinha: $($_.InvocationInfo.ScriptLineNumber)" -ForegroundColor DarkGray
}
finally {
    if (Get-Command Pause -ErrorAction SilentlyContinue) {
        Write-Host "`n[*] Script finalizado." -ForegroundColor DarkGray
        Pause
    }
}