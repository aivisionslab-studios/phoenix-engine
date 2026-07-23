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
$pipArgs = @("install", "fastapi", "uvicorn", "psutil", "chromadb", "astor", "google-cloud-firestore")
if (-not $IsWindows) {
    # PEP 668 (externally-managed-environment) bloqueia pip direto em
    # distros como Ubuntu 23.04+. --break-system-packages nao existe
    # no pip do Windows, entao so entra aqui na branch Linux.
    #
    # --ignore-installed evita que o pip tente DESINSTALAR pacotes que
    # ja vieram via apt (ex: click, psutil) antes de atualizar - varios
    # deles nao tem RECORD file (empacotamento debian) e o pip trava
    # com "uninstall-no-record-file". Com essa flag ele so instala a
    # versao nova em /usr/local/.../dist-packages, sem mexer na copia
    # do apt em /usr/lib/.../dist-packages. Path do Python ja prioriza
    # /usr/local antes de /usr/lib, entao a versao nova e' a que vale.
    $pipArgs += "--break-system-packages"
    $pipArgs += "--ignore-installed"
}
$pipExe = if ($IsWindows) { "python" } else { "python3" }
$pipResult = Invoke-Native -Exe $pipExe -Args (@("-m", "pip") + $pipArgs)
if ($pipResult.ExitCode -ne 0) {
    Write-Host "[X] Falha ao instalar dependencias Python (codigo $($pipResult.ExitCode))." -ForegroundColor Red
    Write-Host ($pipResult.Output -join "`n") -ForegroundColor DarkGray
    if (Get-Command Pause -ErrorAction SilentlyContinue) { Pause }
    exit 1
}
Write-Host "[OK] Dependencias Python instaladas." -ForegroundColor Green

# Provisionamento de Containers Docker (identico em Windows/Linux - o
# daemon ja foi garantido por windows.ps1/linux.ps1 antes de chegarmos aqui)
Write-Host "`n=== PROVISIONAMENTO DE CONTAINERS ===" -ForegroundColor Cyan

Write-Host "[*] Provisionando Ollama..."

# Em muitas distros Linux o Ollama roda instalado nativamente como
# servico systemd, ja ocupando a porta 11434 fora do Docker. Se nao
# pararmos ele antes, o "docker run -p 11434:11434" falha com
# "address already in use". No Windows o equivalente e o processo
# "ollama app.exe" / servico "Ollama".
if (-not $IsWindows) {
    $svcCheck = Invoke-Native -Exe "systemctl" -Args @("is-active", "--quiet", "ollama")
    if ($svcCheck.ExitCode -eq 0) {
        Write-Host "[*] Servico nativo 'ollama' esta ativo e ocupando a porta 11434. Parando..." -ForegroundColor Yellow
        Invoke-Native -Exe "sudo" -Args @("systemctl", "stop", "ollama") | Out-Null
        Invoke-Native -Exe "sudo" -Args @("systemctl", "disable", "ollama") | Out-Null
    }
} else {
    $svcCheck = Invoke-Native -Exe "sc.exe" -Args @("query", "Ollama")
    if ($svcCheck.ExitCode -eq 0) {
        Write-Host "[*] Servico nativo 'Ollama' detectado no Windows. Parando..." -ForegroundColor Yellow
        Invoke-Native -Exe "sc.exe" -Args @("stop", "Ollama") | Out-Null
    }
    Invoke-Native -Exe "taskkill" -Args @("/IM", "ollama app.exe", "/F") | Out-Null
}

Invoke-Native -Exe "docker" -Args @("volume","create","ollama") | Out-Null
Invoke-Native -Exe "docker" -Args @("rm","-f","ollama") | Out-Null
# --dns explicito: o log mostrou falha de resolucao ("lookup registry.ollama.ai
# ... no such host") batendo no DNS do roteador local (192.168.15.1). Usando
# 1.1.1.1/8.8.8.8 direto no container evitamos depender desse resolver.
$run = Invoke-Native -Exe "docker" -Args @("run","-d","--name","ollama","--restart","unless-stopped","-p","11434:11434","--dns","1.1.1.1","--dns","8.8.8.8","-v","ollama:/root/.ollama","ollama/ollama")
if ($run.ExitCode -ne 0) {
    Write-Host "[X] Falha ao subir o container do Ollama (codigo $($run.ExitCode))." -ForegroundColor Red
    Write-Host ($run.Output -join "`n") -ForegroundColor DarkGray
    if ($run.Output -join "`n" -match "address already in use|port is already allocated") {
        Write-Host "[!] A porta 11434 ainda esta ocupada por outro processo. Rode 'sudo lsof -i :11434' (Linux) ou 'netstat -ano | findstr 11434' (Windows) para identificar quem esta segurando a porta e encerre manualmente." -ForegroundColor DarkYellow
    }
    if (Get-Command Pause -ErrorAction SilentlyContinue) { Pause }
    exit 1
}
Write-Host "[OK] Container Ollama no ar." -ForegroundColor Green

function Invoke-OllamaPull {
    param([Parameter(Mandatory)][string]$Model, [int]$MaxAttempts = 3)
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        Write-Host "[*] Baixando modelo $Model para o Ollama (tentativa $attempt/$MaxAttempts, pode demorar alguns minutos)..." -ForegroundColor Yellow
        docker exec ollama ollama pull $Model
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Modelo $Model baixado." -ForegroundColor Green
            return $true
        }
        Write-Host "[!] Pull de $Model falhou (codigo $LASTEXITCODE)." -ForegroundColor DarkYellow
        if ($attempt -lt $MaxAttempts) {
            Write-Host "    Aguardando 10s antes de tentar de novo (comum apos falha de DNS/rede)..." -ForegroundColor DarkGray
            Start-Sleep -Seconds 10
        }
    }
    Write-Host "[X] Nao foi possivel baixar $Model apos $MaxAttempts tentativas. Rode manualmente depois: docker exec ollama ollama pull $Model" -ForegroundColor Red
    return $false
}

Start-Sleep -Seconds 5
Invoke-OllamaPull -Model "qwen3:8b" | Out-Null
# nomic-embed-text e' o modelo de embedding que o RAG (KnowledgeEngine) usa -
# sem ele a base vetorial fica vazia (RAG DOCUMENTS: 0 no dashboard) e a API
# tenta baixar sozinha em runtime, o que so funciona se a rede/DNS estiver ok.
# Baixando aqui, com retry, evita cair nesse caminho instavel depois.
Invoke-OllamaPull -Model "nomic-embed-text" | Out-Null

Write-Host "[*] Provisionando Open WebUI..."

# "port is already allocated" na 3000 costuma ser um container orfao (de uma
# execucao anterior que falhou/foi interrompida) ainda segurando a porta,
# mesmo com nome diferente de "open_webui". Derruba qualquer container
# publicando a 3000 antes de tentar subir o nosso.
$stalePort3000 = Invoke-Native -Exe "docker" -Args @("ps", "-aq", "--filter", "publish=3000")
if ($stalePort3000.ExitCode -eq 0 -and $stalePort3000.Output) {
    foreach ($containerId in ($stalePort3000.Output -split "`n" | Where-Object { $_.Trim() })) {
        Write-Host "[*] Removendo container orfao $containerId que esta segurando a porta 3000..." -ForegroundColor Yellow
        Invoke-Native -Exe "docker" -Args @("rm", "-f", $containerId.Trim()) | Out-Null
    }
}

Invoke-Native -Exe "docker" -Args @("volume","create","open-webui") | Out-Null
Invoke-Native -Exe "docker" -Args @("rm","-f","open_webui") | Out-Null
$runWebui = Invoke-Native -Exe "docker" -Args @("run","-d","--name","open_webui","--restart","unless-stopped","-p","3000:8080","--add-host=host.docker.internal:host-gateway","-e","OLLAMA_BASE_URL=http://host.docker.internal:11434","-v","open-webui:/app/backend/data","ghcr.io/open-webui/open-webui:main")
if ($runWebui.ExitCode -ne 0) {
    Write-Host "[!] Falha ao subir o Open WebUI (codigo $($runWebui.ExitCode)). Prosseguindo mesmo assim." -ForegroundColor DarkYellow
    Write-Host ($runWebui.Output -join "`n") -ForegroundColor DarkGray
    if ($runWebui.Output -join "`n" -match "address already in use|port is already allocated") {
        Write-Host "[!] A porta 3000 ainda esta ocupada. Rode 'sudo lsof -i :3000' (Linux) ou 'netstat -ano | findstr 3000' (Windows) para identificar o processo." -ForegroundColor DarkYellow
    }
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
    "Ollama"               = "https://github.com/ollama/ollama.git"
    "Whisper.cpp"          = "https://github.com/ggml-org/whisper.cpp.git"
}
if ($IsWindows) {
    # LibreHardwareMonitor e' uma lib .NET consumida via pythonnet no core.py
    # do Windows - o path Linux (sysfs/DRM) nao usa e nunca vai usar esse repo.
    $Repos["LibreHardwareMonitor"] = "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor.git"
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
