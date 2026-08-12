# Engine/Bootstrap/Start-PhoenixServer.ps1
param ([string]$PhoenixRoot)

 $ErrorActionPreference = "Stop"
 $result = @{ Name = "Phoenix API"; Success = $false; RestartRequired = $false; Elapsed = 0; Warnings = @(); Errors = @() }
 $sw = [Diagnostics.Stopwatch]::StartNew()

try {
    Set-Location $PhoenixRoot
    $pythonExe = if ($IsWindows) { ".\.venv\Scripts\python.exe" } else { ".\.venv/bin/python" }
    if (-not (Test-Path $pythonExe)) { throw "Python virtual environment nao encontrado em $pythonExe" }

    Write-Host "[*] Iniciando api_server.py em background..."
    $proc = Start-Process -FilePath $pythonExe -ArgumentList "api_server.py" -PassThru

    Start-Sleep -Seconds 2
    if ($proc.HasExited) { throw "api_server encerrou prematuramente. Codigo de saida: $($proc.ExitCode)" }

    Write-Host "[*] Aguardando API inicializar (Health Check)..."
    $apiReady = $false
    $HealthTimeout = 60
    $PhoenixHealthEndpoint = "/health"

    for ($i = 1; $i -le ($HealthTimeout / 2); $i++) {
        Start-Sleep -Seconds 2
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000$PhoenixHealthEndpoint" -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) { $apiReady = $true; break }
        } catch { Write-Host "    Aguardando API... ($i)" -ForegroundColor DarkGray }
    }

    if ($apiReady) {
        Write-Host "[OK] Phoenix API esta online e respondendo." -ForegroundColor Green
        $result.Success = $true
    } else {
        throw "API iniciada, mas nao respondeu ao Health Check em $HealthTimeout segundos."
    }
} catch {
    $result.Errors += $_.Exception.Message
} finally {
    $sw.Stop()
    $result.Elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 1)
}
return $result
