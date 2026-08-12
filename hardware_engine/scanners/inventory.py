"""
scanners/inventory.py
========================
Inventário geral: programas instalados, runtimes, bibliotecas, SDKs,
compiladores. Não há API universal para "listar tudo que está instalado"
entre Windows/Linux/WSL, então combinamos fontes específicas de cada
plataforma, sempre best-effort.
"""

from __future__ import annotations

import platform
from typing import Any

from ._utils import run_cmd, command_exists, safe


def _windows_programs() -> list[dict[str, Any]]:
    out = run_cmd([
        "powershell", "-NoProfile", "-Command",
        "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* "
        "| Select-Object DisplayName,DisplayVersion | ConvertTo-Csv -NoTypeInformation",
    ])
    programs = []
    if not out:
        return programs
    lines = out.splitlines()[1:]
    for line in lines:
        parts = [p.strip('"') for p in line.split('","')]
        if parts and parts[0]:
            programs.append({
                "name": parts[0].strip('"'),
                "version": parts[1].strip('"') if len(parts) > 1 else None,
            })
    return programs


def _linux_programs() -> list[dict[str, Any]]:
    if command_exists("dpkg"):
        out = run_cmd(["dpkg-query", "-W", "-f=${Package}\t${Version}\n"])
        if out:
            programs = []
            for line in out.splitlines():
                if "\t" in line:
                    name, version = line.split("\t", 1)
                    programs.append({"name": name, "version": version})
            return programs
    if command_exists("rpm"):
        out = run_cmd(["rpm", "-qa", "--qf", "%{NAME}\t%{VERSION}\n"])
        if out:
            programs = []
            for line in out.splitlines():
                if "\t" in line:
                    name, version = line.split("\t", 1)
                    programs.append({"name": name, "version": version})
            return programs
    return []


def scan_installed_programs() -> list[dict[str, Any]]:
    system = platform.system()
    if system == "Windows":
        return safe(_windows_programs, []) or []
    if system == "Linux":
        return safe(_linux_programs, []) or []
    return []


TOOLCHAIN_COMMANDS = {
    "python": ["python3", "--version"],
    "pip": ["pip3", "--version"],
    "node": ["node", "--version"],
    "npm": ["npm", "--version"],
    "git": ["git", "--version"],
    "gcc": ["gcc", "--version"],
    "clang": ["clang", "--version"],
    "cmake": ["cmake", "--version"],
    "make": ["make", "--version"],
    "docker": ["docker", "--version"],
    "conda": ["conda", "--version"],
}


def scan_toolchain() -> list[dict[str, Any]]:
    found = []
    for name, cmd in TOOLCHAIN_COMMANDS.items():
        if not command_exists(cmd[0]):
            continue
        version = run_cmd(cmd)
        found.append({"name": name, "version": (version.splitlines()[0] if version else None)})
    return found


def scan_inventory() -> dict[str, Any]:
    return {
        "installed_programs": scan_installed_programs(),
        "toolchain": scan_toolchain(),
    }
