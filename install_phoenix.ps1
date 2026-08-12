# install_phoenix.ps1
# Bootstrapper Oficial da Phoenix Engine 5.0 - Enterprise Grade

# =====================================================================
# POLÍTICA DE ROTEAMENTO DE HARDWARE (DEFINITIVA)
# Regra imutável de alocação para evitar disputa de VRAM e garantir estabilidade:
# 1. Modelos de Chatbot/LLM (Texto) -> 100% CPU via llama.cpp (sem -ngl)
# 2. Modelos de Imagem (SD/FLUX) -> 100% GPU via stable-diffusion.cpp (Vulkan)
# =====================================================================
 $env:PHOENIX_LLM_DEVICE = "CPU"
 $env:PHOENIX_IMAGE_DEVICE = "GPU"
 $env:PHOENIX_LLM_NGL = "0" # Força 0 camadas na GPU para LLMs

# CORREÇÃO BUG-001: Força UTF-8 no PS 5.1 para não quebrar acentos na fase inicial
if ($PSVersionTable.PSVersion.Major -lt 6) {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
}

 $ErrorActionPreference = "Stop"
 $ProgressPreference = "SilentlyContinue"
 $env:GIT_TERMINAL_PROMPT = "0"

 $PhoenixRoot = $PSScriptRoot
 $InstallDir = Join-Path $PhoenixRoot "install"
Set-Location $PhoenixRoot

# Setup de Logs
 $logDir = Join-Path $PhoenixRoot "logs/install"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
 $logFile = Join-Path $logDir "install_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
 $jsonLogFile = Join-Path $logDir "install_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
Start-Transcript -Path $logFile -Force | Out-Null

 $report = @()
 $needsRestart = $false
 $warningCount = 0
 $osRestartPending = $false
 $fatalError = $false

function Write-StructuredLog {
    param([hashtable]$Result)
    $logEntry = @{
        timestamp = $Result.Timestamp
        module = $Result.Name
        success = $Result.Success
        error_code = $Result.ErrorCode
        duration = $Result.Duration
        warnings = $Result.Warnings
    }
    $logEntry | ConvertTo-Json -Compress | Out-File -FilePath $jsonLogFile -Append -Encoding utf8
}

function Invoke-Step {
    param([string]$Name, [string]$ScriptPath, [hashtable]$Arguments = @{})
    
    if (-not (Test-Path $ScriptPath)) {
        return @{ Name = $Name; Success = $false; ErrorCode = "PX000"; Errors = @("Arquivo nao encontrado: $ScriptPath"); Warnings = @(); RestartRequired = $false; Duration = 0; Timestamp = Get-Date; Artifacts = @(); Version = "N/A" }
    }

    $sw = [Diagnostics.Stopwatch]::StartNew()
    $rawResult = & $ScriptPath @Arguments
    $sw.Stop()
    
    # Validação estrita do contrato (Hashtable com chaves obrigatórias)
    $requiredKeys = @("Success", "Errors", "Warnings", "Artifacts", "RestartRequired")
    $isValid = $true
    
    if ($rawResult -isnot [System.Collections.IDictionary]) {
        $isValid = $false
    } else {
        foreach ($key in $requiredKeys) {
            if (-not $rawResult.ContainsKey($key)) { $isValid = $false; break }
        }
    }

    if (-not $isValid) {
        $rawResult = @{ Success = $false; ErrorCode = "PX002"; Errors = @("Modulo nao retornou um contrato Hashtable valido."); Warnings = @(); RestartRequired = $false; Artifacts = @(); Version = "N/A" }
    }

    $rawResult.Name = $Name
    $rawResult.Duration = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    if (-not $rawResult.Timestamp) { $rawResult.Timestamp = Get-Date }
    if (-not $rawResult.ErrorCode) { $rawResult.ErrorCode = "PX000" }
    
    Write-StructuredLog -Result $rawResult
    return $rawResult
}

try {
    Write-Host "==================================" -ForegroundColor Cyan
    Write-Host "   PHOENIX ENGINE 5.0 BOOTSTRAP   " -ForegroundColor Cyan
    Write-Host "==================================" -ForegroundColor Cyan
    Write-Host " -> Politica de Hardware: LLM=CPU | IMAGE=GPU" -ForegroundColor Yellow

    # CORREÇÃO: Git é o PRIMEIRO passo de todos, antes até do PowerShell 7.
    # winget/apt-get não dependem de PS7 pra funcionar, e sem Git nada mais
    # (nem a clonagem dos 45 repos no common.ps1) tem como acontecer.
    # Detecção de plataforma "PS5.1-safe": Windows PowerShell 5.1 só existe
    # no Windows, então nesse caso $__isWinEarly é sempre $true sem precisar
    # de $IsWindows (que nem existe no PS 5.1).
    $__isWinEarly = ($PSVersionTable.PSVersion.Major -lt 6) -or ($IsWindows -eq $true)
    $__isLinuxEarly = ($PSVersionTable.PSVersion.Major -ge 6) -and ($IsLinux -eq $true)

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "[*] Git nao encontrado. Instalando (primeiro passo do bootstrap)..." -ForegroundColor Yellow
        if ($__isWinEarly) {
            if (Get-Command winget -ErrorAction SilentlyContinue) {
                & winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
            } else {
                Write-Host "[X] winget nao encontrado - nao e possivel instalar o Git automaticamente." -ForegroundColor Red
            }
        } elseif ($__isLinuxEarly) {
            $needsSudo = (id -u) -ne "0"
            $aptPrefix = if ($needsSudo -and (Get-Command sudo -ErrorAction SilentlyContinue)) { "sudo" } else { "" }
            Invoke-Expression "$aptPrefix apt-get update -y" 2>&1 | Out-Null
            Invoke-Expression "$aptPrefix apt-get install -y git" 2>&1 | Out-Null
        }
        if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
            throw "[PX001] Git nao pode ser instalado automaticamente. Instale manualmente (winget install Git.Git / apt-get install git) e rode o instalador novamente."
        }
    }
    Write-Host "[OK] Git disponivel em: $((Get-Command git).Source)" -ForegroundColor Green

    # 0. GARANTIR POWERSHELL 7 LTS (Passa o caminho do bootstrap explicitamente)
    $psResult = Invoke-Step "PowerShell" (Join-Path $InstallDir "powershell.ps1") -Arguments @{ BootstrapPath = $PSCommandPath }
    $report += $psResult
    
    # Se o módulo avisar que precisa reiniciar (porque acabou de instalar o PS7)
    if ($psResult.RestartRequired) {
        $pwshPath = "$env:ProgramFiles\PowerShell\7\pwsh.exe"
        if (Test-Path $pwshPath) {
            Write-Host "[*] Reexecutando bootstrap no PowerShell 7..." -ForegroundColor Green
            Stop-Transcript | Out-Null
            
            # CORREÇÃO BUG-001: -NoNewWindow faz o PS7 rodar nesta mesma janela.
            # -Wait faz o PS5.1 segurar a janela até o PS7 terminar toda a instalação.
            Start-Process $pwshPath -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"" -Wait -NoNewWindow
            
            # Saída limpa após o PS7 concluir
            exit
        }
    }

    if (-not $psResult.Success) { throw "[$($psResult.ErrorCode)] $($psResult.Errors[0])" }

    # CORREÇÃO DO BUG "Sistema operacional nao suportado" no Windows puro:
    # se chegamos até aqui ainda no PS 5.1 (o step PowerShell reportou
    # sucesso mas não reiniciou pra PS7 de verdade - ex: winget do PS7
    # falhou silenciosamente), $IsWindows/$IsLinux NÃO EXISTEM no PS 5.1
    # e sempre caem no "else". Windows PowerShell 5.1 só roda no Windows,
    # então tratamos isso como Windows em vez de travar o provisionamento.
    if ($PSVersionTable.PSVersion.Major -ge 6) {
        $osScriptName = if ($IsWindows) { "windows.ps1" } elseif ($IsLinux) { "linux.ps1" } else { throw "Sistema operacional nao suportado (PS7 sem IsWindows/IsLinux)." }
    } else {
        Write-Host "[!] Continuando em Windows PowerShell 5.1 (upgrade pro PS7 nao foi confirmado). Alguns recursos podem ficar limitados." -ForegroundColor Yellow
        $osScriptName = "windows.ps1"

        # CORREÇÃO CRÍTICA: storage_scanner.ps1 (2x) e common.ps1 (13x)
        # checam $IsWindows diretamente, não passam pelo $osScriptName.
        # Em PS 5.1 essa variável nunca existiu de verdade (é $null),
        # então mesmo sabendo aqui que é Windows, esses dois arquivos
        # cairiam no branch Linux por engano. Definindo manualmente em
        # escopo global, qualquer script chamado depois (mesmo em scope
        # filho via '&') enxerga o valor certo.
        $global:IsWindows = $true
        $global:IsLinux = $false
        $global:IsMacOS = $false
    }

    # 1. SCANNER DE ARMAZENAMENTO
    $report += Invoke-Step "Storage" (Join-Path $InstallDir "storage_scanner.ps1")
    if (-not $report[-1].Success) { throw "[$($report[-1].ErrorCode)] $($report[-1].Errors[0])" }

    # 2. CAMADA ESPECIFICA DO SO
    $report += Invoke-Step "OS" (Join-Path $InstallDir $osScriptName)
    if (-not $report[-1].Success) { throw "[$($report[-1].ErrorCode)] $($report[-1].Errors[0])" }

    # CORREÇÃO BUG-002: se o modulo OS instalou algo que exige reinicio/relogin
    # (ex: Docker Desktop recem-instalado no Windows), paramos AQUI em vez de
    # seguir pro Common e tentar usar um Docker que ainda nao terminou de subir.
    if ($report[-1].RestartRequired) {
        Write-Host "`n[!] Pre-requisitos foram instalados e precisam de reinicio/relogin antes de continuar." -ForegroundColor Yellow
        Write-Host "    (Normalmente: Docker Desktop recem-instalado. Abra-o manualmente uma vez e faça login.)" -ForegroundColor Yellow
        Write-Host "    Depois disso, rode o instalador novamente para concluir o provisionamento." -ForegroundColor Yellow
        $needsRestart = $true
        $osRestartPending = $true
        Stop-Transcript | Out-Null
        exit
    }

    # 3. CAMADA COMUM
    $report += Invoke-Step "Common" (Join-Path $InstallDir "common.ps1")
    if (-not $report[-1].Success) { throw "[$($report[-1].ErrorCode)] $($report[-1].Errors[0])" }

} catch {
    Write-Host "`n[X] ERRO FATAL DURANTE O PROVISIONAMENTO:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    $fatalError = $true
} finally {
    # Se estamos reiniciando, não imprimimos o relatório ainda (ele será impresso no final do PS7)
    if (-not (($psResult -and $psResult.RestartRequired) -or $osRestartPending)) {
        Write-Host "`n===================================" -ForegroundColor Cyan
        Write-Host "      PHOENIX INSTALL REPORT        " -ForegroundColor Cyan
        Write-Host "===================================" -ForegroundColor Cyan
        Write-Host "PowerShell ......... $($PSVersionTable.PSVersion.ToString())" -ForegroundColor Gray
        
        foreach ($entry in $report) {
            $status = if ($entry.Success) { "OK" } else { "Failed" }
            $color = if ($entry.Success) { "Green" } else { "Red" }
            $time = $entry.Duration
            $version = if ($entry.Version -and $entry.Version -ne "N/A") { "v$($entry.Version)" } else { "" }
            
            Write-Host ("{0,-12} {1,-10} {2,-10} Tempo: {3}s" -f "$($entry.Name)...", $status, $version, $time) -ForegroundColor $color
            
            if ($entry.Warnings.Count -gt 0) {
                $warningCount += $entry.Warnings.Count
                Write-Host "    Warnings: $($entry.Warnings -join ', ')" -ForegroundColor Yellow
            }
            if ($entry.RestartRequired) { $needsRestart = $true }
        }
        
        Write-Host "-----------------------------------" -ForegroundColor Cyan
        Write-Host "Restart Required .. $(if ($needsRestart) {'YES'} else {'NO'})" -ForegroundColor $(if ($needsRestart) {'Yellow'} else {'Gray'})
        Write-Host "Warnings .......... $warningCount" -ForegroundColor $(if ($warningCount -gt 0) {'Yellow'} else {'Gray'})
        Write-Host "Log (Texto) ....... $logFile" -ForegroundColor DarkGray
        Write-Host "Log (JSON) ........ $jsonLogFile" -ForegroundColor DarkGray
        Write-Host "===================================`n" -ForegroundColor Cyan
        
        Stop-Transcript | Out-Null
        
        # Saída limpa
        if ($Host.Name -eq "ConsoleHost") { Read-Host "Pressione ENTER para sair" }
    }
}

# CORREÇÃO: sem isso, o processo sempre terminava com exit code 0, mesmo
# apos um erro fatal (a excecao era capturada e so impressa, nunca
# repropagada). Qualquer .bat/.sh que chame este script e cheque
# ERRORLEVEL/$? nunca detectava falha real - inclusive o Iniciar_Phoenix.bat.
if ($fatalError) {
    exit 1
}
# Phoenix Engine 3.0 © 2026
