# install/common.ps1
# Camada comum a Windows e Linux: dependencias Python cross-platform,
# provisionamento dos containers Docker, clonagem dos repositorios, e
# lancamento final da API. So roda depois que windows.ps1 ou linux.ps1
# ja garantiram Python, pip, Docker e privilegios corretos.

function Invoke-Native {
    param([Parameter(Mandatory)][string]$Exe, [Parameter(Mandatory)][string[]]$Args)
    $output = & $Exe @Args 2>&1 | ForEach-Object { $_.ToString() }
    return @{ Output = $output; ExitCode = $LASTEXITCODE }
}

# Dependencias Python cross-platform (nada de HardwareMonitor/wmi/pywin32
# aqui - isso ja foi instalado so no Windows por windows.ps1, e o Linux
# instalou pyudev separadamente em linux.ps1)
Write-Host "`n=== CONFIGURACAO DO KERNEL (PYTHON, CROSS-PLATFORM) ===" -ForegroundColor Cyan
pip install fastapi uvicorn psutil chromadb astor

# Provisionamento de Containers Docker (identico em Windows/Linux - o
# daemon ja foi garantido por windows.ps1/linux.ps1 antes de chegarmos aqui)
Write-Host "`n=== PROVISIONAMENTO DE CONTAINERS ===" -ForegroundColor Cyan

Write-Host "[*] Provisionando Ollama..."
Invoke-Native -Exe "docker" -Args @("volume","create","ollama") | Out-Null
Invoke-Native -Exe "docker" -Args @("rm","-f","ollama") | Out-Null
$run = Invoke-Native -Exe "docker" -Args @("run","-d","--name","ollama","--restart","unless-stopped","-p","11434:11434","-v","ollama:/root/.ollama","ollama/ollama")
if ($run.ExitCode -ne 0) {
    Write-Host "[X] Falha ao subir o container do Ollama (codigo $($run.ExitCode))." -ForegroundColor Red
    Write-Host ($run.Output -join "`n") -ForegroundColor DarkGray
    if (Get-Command Pause -ErrorAction SilentlyContinue) { Pause }
    exit 1
}
Write-Host "[OK] Container Ollama no ar." -ForegroundColor Green

Write-Host "[*] Baixando modelo qwen3:8b para o Ollama (isso pode demorar alguns minutos)..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
docker exec ollama ollama pull qwen3:8b
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] O pull do modelo qwen3:8b retornou codigo $LASTEXITCODE (rede/timeout). Prosseguindo mesmo assim." -ForegroundColor DarkYellow
} else {
    Write-Host "[OK] Modelo qwen3:8b baixado." -ForegroundColor Green
}

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

# Clonagem de Motores de IA e Codigo Oficial via Git (identico nos 2 SOs)
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

if (-not (Test-Path "./repos")) {
    New-Item -ItemType Directory -Force -Path "./repos" | Out-Null
}

foreach ($repo in $Repos.Keys) {
    $dest = Join-Path "./repos" $repo
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

# Verifica se o codigo fonte da Phoenix esta presente antes de tentar subir a API
if (-not (Test-Path "./api_server.py")) {
    Write-Host "[X] Arquivo api_server.py nao encontrado na raiz do projeto! O codigo fonte da Phoenix esta faltando." -ForegroundColor Red
    if (Get-Command Pause -ErrorAction SilentlyContinue) { Pause }
    exit 1
}

# Inicializacao da Phoenix (a API assume o controle a partir daqui)
Write-Host "`n=== INICIANDO PHOENIX ENGINE ===" -ForegroundColor Green
Write-Host "[*] Provisionamento concluido. Passando o controle para a API Python..." -ForegroundColor DarkGray
Write-Host "[*] Pressione Ctrl+C para parar o servidor." -ForegroundColor DarkGray

if ($IsWindows) {
    python api_server.py
} else {
    python3 api_server.py
}
