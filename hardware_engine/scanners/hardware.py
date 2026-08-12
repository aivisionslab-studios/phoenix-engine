"""
scanners/hardware.py
=====================
Observação pura de hardware. Nada aqui decide nada — apenas lê e retorna
dicts serializáveis. GPUs AMD (o caso do RX 580 / GCN4 no stack da
AIVisionsLab) não têm um equivalente confiável e multiplataforma ao
`nvidia-smi`; por isso o scanner tenta várias fontes em cascata
(rocm-smi -> vulkaninfo -> lspci/WMI) e marca explicitamente qual fonte
respondeu. Quando nenhuma fonte funciona, o campo vem como None — nunca
inventamos valor.
"""

from __future__ import annotations

import json
import platform
import re
from typing import Any, Optional

import psutil

from ._utils import run_cmd, command_exists, safe


def scan_cpu_temperature() -> Optional[float]:
    """Best-effort: `psutil.sensors_temperatures()` só existe/funciona no
    Linux (via /sys/class/hwmon). No Windows/Mac não há API estável e
    multiplataforma sem dependência extra — retorna None em vez de
    inventar valor, mesmo padrão adotado pelo scanner de GPU."""
    if not hasattr(psutil, "sensors_temperatures"):
        return None
    temps = safe(psutil.sensors_temperatures) or {}
    for key in ("coretemp", "k10temp", "cpu_thermal", "zenpower"):
        entries = temps.get(key)
        if entries:
            pkg = next((e for e in entries if "package" in e.label.lower()), entries[0])
            return float(pkg.current)
    for entries in temps.values():
        if entries:
            return float(entries[0].current)
    return None


def detect_cpu_throttling(cpu_info: dict[str, Any]) -> Optional[bool]:
    """Heurística best-effort, NÃO uma leitura direta de um flag de
    throttling do fabricante (que exigiria `turbostat`/root ou
    ferramentas específicas por vendor). Sinaliza `True` apenas quando
    current_freq_mhz cai abaixo de 60% de max_freq_mhz com utilização
    alta simultânea — um indício, não uma certeza. Retorna `None`
    (nunca inventa `False`) quando frequência máxima é desconhecida."""
    current = cpu_info.get("current_freq_mhz")
    maximum = cpu_info.get("max_freq_mhz")
    utilization = cpu_info.get("utilization_percent")
    if current is None or not maximum:
        return None
    if utilization is not None and utilization > 70 and current < 0.6 * maximum:
        return True
    return False


def scan_cpu() -> dict[str, Any]:
    freq = safe(psutil.cpu_freq)
    load = None
    if hasattr(psutil, "getloadavg"):
        load = safe(psutil.getloadavg)
    return {
        "logical_cores": psutil.cpu_count(logical=True),
        "physical_cores": psutil.cpu_count(logical=False),
        "utilization_percent": psutil.cpu_percent(interval=0.2),
        "per_core_percent": psutil.cpu_percent(interval=0.0, percpu=True),
        "current_freq_mhz": getattr(freq, "current", None) if freq else None,
        "max_freq_mhz": getattr(freq, "max", None) if freq else None,
        "load_average": load,
        "temperature_celsius": scan_cpu_temperature(),
    }


def scan_memory() -> dict[str, Any]:
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    return {
        "ram": {
            "total_bytes": vm.total,
            "used_bytes": vm.used,
            "available_bytes": vm.available,
            "percent_used": vm.percent,
        },
        "swap": {
            "total_bytes": sw.total,
            "used_bytes": sw.used,
            "percent_used": sw.percent,
        },
    }


def _disk_kind_guess(mountpoint: str, device: str) -> str:
    device_l = device.lower()
    if "nvme" in device_l:
        return "NVMe"
    if re.match(r"^/dev/sd|^[c-z]:", device_l):
        return "SSD/HDD (indeterminado via SO)"
    return "desconhecido"


def _disk_health_status(device: str) -> Optional[str]:
    """Best-effort via `smartctl -H --json <device>` (pacote smartmontools).
    Sem smartctl instalado, ou sem permissão para ler o device (comum sem
    root/admin), retorna None — nunca inventa 'OK'. Valores possíveis
    quando a leitura funciona: 'PASSED', 'FAILED', ou o texto bruto que o
    smartctl reportou quando o resultado não é um booleano simples."""
    if not command_exists("smartctl"):
        return None
    out = run_cmd(["smartctl", "-H", "--json", device])
    if not out:
        return None
    try:
        data = json.loads(out)
    except Exception:
        return None
    smart_status = data.get("smart_status", {})
    if "passed" in smart_status:
        return "PASSED" if smart_status["passed"] else "FAILED"
    return safe(lambda: data.get("smart_status", {}).get("nvme", {}).get("value"))


def scan_storage() -> list[dict[str, Any]]:
    disks = []
    for part in safe(psutil.disk_partitions, []) or []:
        usage = safe(lambda: psutil.disk_usage(part.mountpoint))
        if usage is None:
            continue
        disks.append({
            "device": part.device,
            "mountpoint": part.mountpoint,
            "fstype": part.fstype,
            "kind_guess": _disk_kind_guess(part.mountpoint, part.device),
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "percent_used": usage.percent,
            "health_status": _disk_health_status(part.device),
        })
    return disks


def _scan_gpu_rocm() -> list[dict[str, Any]] | None:
    if not command_exists("rocm-smi"):
        return None
    out = run_cmd(["rocm-smi", "--showtemp", "--showuse", "--showmeminfo", "vram",
                   "--showclocks", "--json"])
    if not out:
        return None
    import json
    try:
        data = json.loads(out)
    except Exception:
        return None
    gpus = []
    for card, info in data.items():
        gpus.append({
            "id": card,
            "source": "rocm-smi",
            "temperature_c": safe(lambda: float(list(info.get("Temperature", {}).values())[0])),
            "utilization_percent": safe(lambda: float(info.get("GPU use (%)"))),
            "vram_total_bytes": safe(lambda: int(info.get("VRAM Total Memory (B)"))),
            "vram_used_bytes": safe(lambda: int(info.get("VRAM Total Used Memory (B)"))),
            "raw": info,
        })
    return gpus or None


def _scan_gpu_vulkan() -> list[dict[str, Any]] | None:
    if not command_exists("vulkaninfo"):
        return None
    out = run_cmd(["vulkaninfo", "--summary"])
    if not out:
        return None
    gpus = []
    for line in out.splitlines():
        m = re.search(r"deviceName\s*=\s*(.+)", line)
        if m:
            gpus.append({
                "id": f"vulkan-{len(gpus)}",
                "source": "vulkaninfo",
                "name": m.group(1).strip(),
                "temperature_c": None,
                "utilization_percent": None,
                "vram_total_bytes": None,
                "vram_used_bytes": None,
            })
    return gpus or None


def _scan_gpu_fallback() -> list[dict[str, Any]] | None:
    system = platform.system()
    if system == "Linux" and command_exists("lspci"):
        out = run_cmd(["lspci"])
        if out:
            gpus = [{"id": f"lspci-{i}", "source": "lspci", "name": line.split(": ", 1)[-1],
                     "temperature_c": None, "utilization_percent": None,
                     "vram_total_bytes": None, "vram_used_bytes": None}
                    for i, line in enumerate(out.splitlines())
                    if "VGA" in line or "3D controller" in line or "Display controller" in line]
            return gpus or None
    if system == "Windows" and command_exists("wmic"):
        out = run_cmd(["wmic", "path", "win32_VideoController", "get", "name"])
        if out:
            names = [l.strip() for l in out.splitlines()[1:] if l.strip()]
            return [{"id": f"wmic-{i}", "source": "wmic", "name": n,
                     "temperature_c": None, "utilization_percent": None,
                     "vram_total_bytes": None, "vram_used_bytes": None}
                    for i, n in enumerate(names)] or None
    return None


def scan_gpu() -> list[dict[str, Any]]:
    """
    Cascata de fontes para GPU/VRAM: rocm-smi > vulkaninfo > lspci/wmic.
    Nenhuma fonte AMD "oficial" e universal existe para telemetria fina
    de VRAM/temperatura fora do ROCm (que nem sempre está presente em
    setups Vulkan-only como o da AIVisionsLab). Quando nenhuma fonte
    responde, retorna lista vazia — nunca inventa dado.
    """
    for scanner in (_scan_gpu_rocm, _scan_gpu_vulkan, _scan_gpu_fallback):
        result = safe(scanner)
        if result:
            return result
    return []


def scan_hardware() -> dict[str, Any]:
    return {
        "cpu": scan_cpu(),
        "memory": scan_memory(),
        "storage": scan_storage(),
        "gpu": scan_gpu(),
    }
