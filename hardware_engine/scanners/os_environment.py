"""
scanners/os_environment.py
============================
Observação do SO, kernel, distro, WSL, Docker e runtimes de IA
(Vulkan / CUDA / ROCm / DirectML). Detecção é sempre "presença de
evidência" (binário no PATH, arquivo conhecido, variável de ambiente) —
nunca inferência de qualidade ou de decisão de uso.
"""

from __future__ import annotations

import os
import platform
from typing import Any, Optional

from ._utils import run_cmd, command_exists, safe


def _read_os_release() -> dict[str, str]:
    path = "/etc/os-release"
    data: dict[str, str] = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "=" in line:
                    k, _, v = line.strip().partition("=")
                    data[k] = v.strip('"')
    return data


def _is_wsl() -> bool:
    release = platform.uname().release.lower()
    if "microsoft" in release or "wsl" in release:
        return True
    if os.path.exists("/proc/version"):
        try:
            with open("/proc/version", "r", errors="ignore") as f:
                return "microsoft" in f.read().lower()
        except Exception:
            return False
    return False


def scan_os() -> dict[str, Any]:
    uname = platform.uname()
    info: dict[str, Any] = {
        "system": uname.system,
        "release": uname.release,
        "version": uname.version,
        "machine": uname.machine,
        "kernel": uname.release,
        "is_wsl": _is_wsl(),
        "distro": None,
        "build": None,
    }
    if uname.system == "Linux":
        os_release = _read_os_release()
        info["distro"] = os_release.get("PRETTY_NAME") or os_release.get("NAME")
    elif uname.system == "Windows":
        info["build"] = platform.win32_ver()[1] if hasattr(platform, "win32_ver") else None
    return info


def scan_docker() -> dict[str, Any]:
    installed = command_exists("docker")
    running = False
    version = None
    if installed:
        version = run_cmd(["docker", "--version"])
        running = run_cmd(["docker", "info"]) is not None
    return {"installed": installed, "daemon_running": running, "version": version}


def _detect_cuda() -> dict[str, Any]:
    nvcc = run_cmd(["nvcc", "--version"])
    nvidia_smi = run_cmd(["nvidia-smi"])
    return {
        "present": bool(nvcc or nvidia_smi),
        "nvcc_version": nvcc,
        "nvidia_smi_available": nvidia_smi is not None,
    }


def _detect_rocm() -> dict[str, Any]:
    rocminfo = command_exists("rocminfo")
    rocm_smi = command_exists("rocm-smi")
    version = None
    if rocminfo:
        version = run_cmd(["rocminfo"])
    return {"present": rocminfo or rocm_smi, "rocminfo_available": rocminfo,
            "rocm_smi_available": rocm_smi, "detail": (version[:200] if version else None)}


def _detect_vulkan() -> dict[str, Any]:
    available = command_exists("vulkaninfo")
    summary = run_cmd(["vulkaninfo", "--summary"]) if available else None
    return {"present": available, "summary_excerpt": (summary[:400] if summary else None)}


def _detect_directml() -> dict[str, Any]:
    # DirectML é uma DLL do Windows; não há CLI oficial. Checamos presença
    # de artefatos comuns sem afirmar nada sobre funcionalidade.
    candidates = [
        r"C:\Windows\System32\DirectML.dll",
        r"C:\Windows\SysWOW64\DirectML.dll",
    ]
    found = [c for c in candidates if os.path.exists(c)]
    return {"present": bool(found), "found_paths": found}


def scan_runtimes() -> dict[str, Any]:
    return {
        "vulkan": _detect_vulkan(),
        "cuda": _detect_cuda(),
        "rocm": _detect_rocm(),
        "directml": _detect_directml(),
    }


def scan_drivers() -> dict[str, Any]:
    """Best-effort: não há API universal para 'listar todos os drivers'.
    No Linux, expõe módulos de kernel relacionados a GPU via lsmod.
    No Windows, não tentamos parsear o Device Manager aqui (fora de
    escopo sem uma dependência extra); reportamos apenas ausência."""
    system = platform.system()
    if system == "Linux" and command_exists("lsmod"):
        out = run_cmd(["lsmod"])
        gpu_modules = [l.split()[0] for l in (out or "").splitlines()
                       if any(k in l.lower() for k in ("amdgpu", "nvidia", "nouveau", "radeon"))]
        return {"source": "lsmod", "gpu_related_modules": gpu_modules}
    return {"source": None, "gpu_related_modules": []}


def scan_os_environment() -> dict[str, Any]:
    return {
        "os": scan_os(),
        "docker": scan_docker(),
        "runtimes": scan_runtimes(),
        "drivers": scan_drivers(),
    }
