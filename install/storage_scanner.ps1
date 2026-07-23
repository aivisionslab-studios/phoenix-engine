# install/storage_scanner.ps1
# Roda ANTES da camada especifica de SO (chamado pelo install_phoenix.ps1
# na Secao 3). Varre os discos disponiveis, classifica por tipo
# (NVMe > SSD > HDD) e espaco livre, e expoe $Global:PhoenixStorage (lista
# completa) + $Global:PhoenixBestDisk (o disco recomendado) pras camadas
# seguintes (windows.ps1 / linux.ps1 / common.ps1) considerarem ao decidir
# onde colocar volumes Docker, modelos e logs.
#
# Este scanner so informa/recomenda - ele NAO move nada sozinho. Mover o
# data-root do Docker ou a pasta de modelos pro disco recomendado ainda e
# uma decisao manual (fica documentado no final da varredura).

Write-Host "`n=== SCANNER DE ARMAZENAMENTO ===" -ForegroundColor Cyan

$Global:PhoenixStorage = @()

function Get-DiskScore {
    param([string]$Kind, [double]$FreeGB)
    $base = switch ($Kind) {
        "NVMe"  { 100 }
        "SSD"   { 70 }
        "HDD"   { 40 }
        default { 10 }
    }
    # Penaliza discos quase cheios - nao adianta ser NVMe se so tem 5GB livre
    if ($FreeGB -lt 20) { $base = [math]::Floor($base * 0.3) }
    elseif ($FreeGB -lt 50) { $base = [math]::Floor($base * 0.7) }
    return $base
}

if ($IsWindows) {
    try {
        $volumes = Get-Volume -ErrorAction Stop | Where-Object { $_.DriveLetter -and $_.SizeRemaining -gt 0 }
        foreach ($vol in $volumes) {
            $freeGB = [math]::Round($vol.SizeRemaining / 1GB, 1)
            $totalGB = [math]::Round($vol.Size / 1GB, 1)
            $kind = "HDD"
            try {
                $partition = Get-Partition -DriveLetter $vol.DriveLetter -ErrorAction Stop
                $disk = Get-Disk -Number $partition.DiskNumber -ErrorAction Stop
                $physicalDisk = Get-PhysicalDisk -ErrorAction Stop | Where-Object { $_.DeviceId -eq $disk.Number } | Select-Object -First 1
                if ($physicalDisk) {
                    if ($physicalDisk.BusType -eq "NVMe") { $kind = "NVMe" }
                    elseif ($physicalDisk.MediaType -eq "SSD") { $kind = "SSD" }
                    elseif ($physicalDisk.MediaType -eq "HDD") { $kind = "HDD" }
                }
            } catch {
                # Sem permissao ou API indisponivel nessa versao do Windows -
                # assume HDD por seguranca (nunca superestima o disco).
            }

            $score = Get-DiskScore -Kind $kind -FreeGB $freeGB
            $Global:PhoenixStorage += [PSCustomObject]@{
                Path    = "$($vol.DriveLetter):\"
                Kind    = $kind
                FreeGB  = $freeGB
                TotalGB = $totalGB
                Score   = $score
            }
        }
    } catch {
        Write-Host "[!] Nao foi possivel enumerar volumes via Get-Volume/Get-PhysicalDisk: $($_.Exception.Message)" -ForegroundColor DarkYellow
    }
}
elseif ($IsLinux) {
    try {
        $lsblkJson = lsblk -d -b -J -o NAME,ROTA,SIZE,TYPE 2>$null
        $lsblkData = $lsblkJson | ConvertFrom-Json
        $dfLines = df -B1 --output=target,avail 2>$null | Select-Object -Skip 1

        foreach ($dev in $lsblkData.blockdevices) {
            if ($dev.type -ne "disk") { continue }

            $kind = if ($dev.name -like "nvme*") { "NVMe" }
                    elseif ($dev.rota -eq "0" -or $dev.rota -eq $false) { "SSD" }
                    else { "HDD" }

            # Aproximacao: usa o free space do filesystem raiz "/" ja que
            # mapear partition -> disco fisico de forma robusta exigiria
            # parsear lsblk com PKNAME e cruzar com mountpoints - fica como
            # melhoria futura se o usuario tiver varios discos montados.
            $rootLine = $dfLines | Where-Object { ($_ -split '\s+')[0] -eq "/" } | Select-Object -First 1
            $freeBytes = 0
            if ($rootLine) {
                $parts = $rootLine -split '\s+' | Where-Object { $_ -ne "" }
                if ($parts.Count -ge 2) { $freeBytes = [double]$parts[-1] }
            }
            $freeGB = [math]::Round($freeBytes / 1GB, 1)
            $totalGB = [math]::Round(([double]$dev.size) / 1GB, 1)

            $score = Get-DiskScore -Kind $kind -FreeGB $freeGB
            $Global:PhoenixStorage += [PSCustomObject]@{
                Path    = "/dev/$($dev.name)"
                Kind    = $kind
                FreeGB  = $freeGB
                TotalGB = $totalGB
                Score   = $score
            }
        }
    } catch {
        Write-Host "[!] Nao foi possivel enumerar discos via lsblk/df: $($_.Exception.Message)" -ForegroundColor DarkYellow
    }
}

# Politica de escolha: NVMe sempre primeiro, depois SSD SATA, depois HDD -
# so desce de nivel se o nivel de cima nao tiver espaco livre suficiente.
# Isso e uma prioridade FIXA por tipo de disco (nao um score misturado),
# porque na pratica NVMe > SATA SSD > HDD sempre, independente de quao
# cheio o disco mais rapido esteja - a unica coisa que derruba um tier e
# faltar espaco de verdade.
#
# Importante: essa recomendacao vale so pra DADOS MOVEIS (data-root do
# Docker, modelos, pasta de repos) - NAO pros programas instalados via
# winget/apt (Python, Git, Visual Studio Build Tools etc), que sempre vao
# pro caminho padrao do sistema operacional (Program Files no Windows,
# /usr no Linux) independente de qual disco for o "melhor". Alguns desses
# programas dependem de estar na raiz do sistema (normalmente C:\) pra
# funcionar direito, entao o instalador nunca tenta realocar eles.
$MinRequiredFreeGB = 40
$TierOrder = @("NVMe", "SSD", "HDD")

if ($Global:PhoenixStorage.Count -eq 0) {
    Write-Host "[!] Nenhum disco identificado pelo scanner. Prosseguindo sem recomendacao de armazenamento." -ForegroundColor DarkYellow
    $Global:PhoenixBestDisk = $null
} else {
    $Global:PhoenixStorage | Sort-Object Score -Descending | ForEach-Object {
        Write-Host ("    {0,-14} {1,-6} {2,8} GB livres / {3,8} GB total  (score {4})" -f $_.Path, $_.Kind, $_.FreeGB, $_.TotalGB, $_.Score) -ForegroundColor Gray
    }

    $Global:PhoenixBestDisk = $null
    foreach ($tier in $TierOrder) {
        $candidates = $Global:PhoenixStorage | Where-Object { $_.Kind -eq $tier -and $_.FreeGB -ge $MinRequiredFreeGB }
        if ($candidates) {
            $Global:PhoenixBestDisk = $candidates | Sort-Object FreeGB -Descending | Select-Object -First 1
            break
        }
    }

    if (-not $Global:PhoenixBestDisk) {
        # Nenhum disco de nenhum tier tem os $MinRequiredFreeGB GB
        # recomendados livres. Ultimo recurso: ainda respeita a ordem de
        # prioridade NVMe > SSD > HDD, so ignora o minimo de espaco -
        # melhor usar o disco mais rapido disponivel do que travar o
        # instalador por falta de espaco perfeito.
        foreach ($tier in $TierOrder) {
            $candidates = $Global:PhoenixStorage | Where-Object { $_.Kind -eq $tier }
            if ($candidates) {
                $Global:PhoenixBestDisk = $candidates | Sort-Object FreeGB -Descending | Select-Object -First 1
                Write-Host "[!] Nenhum disco tem os $MinRequiredFreeGB GB recomendados livres." -ForegroundColor DarkYellow
                Write-Host "    Usando $($Global:PhoenixBestDisk.Path) ($($Global:PhoenixBestDisk.Kind)) mesmo assim - e o disco mais rapido com mais espaco disponivel." -ForegroundColor DarkYellow
                break
            }
        }
    }

    Write-Host "[OK] Disco recomendado para dados moveis (Docker/modelos/repos): $($Global:PhoenixBestDisk.Path) ($($Global:PhoenixBestDisk.Kind), $($Global:PhoenixBestDisk.FreeGB) GB livres)" -ForegroundColor Green
    Write-Host "[i] Politica: NVMe > SSD SATA > HDD, sempre que houver >= $MinRequiredFreeGB GB livres nesse tier." -ForegroundColor DarkGray
    Write-Host "[i] Programas instalados via winget/apt continuam indo pro caminho padrao do sistema - o scanner nao mexe nisso." -ForegroundColor DarkGray
    Write-Host "[i] O scanner so recomenda - mover o data-root do Docker ou a pasta de modelos pra esse disco ainda e manual (ou automatico, se voce confirmar no passo do Docker)." -ForegroundColor DarkGray
}
