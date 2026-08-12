"""
scanners/services.py
======================
Observação de processos, portas TCP/HTTP em LISTEN e containers Docker.
Não interpreta o que os serviços fazem — apenas relata o que está rodando.
"""

from __future__ import annotations

import json
from typing import Any

import psutil

from ._utils import run_cmd, command_exists, safe


def scan_processes(limit: int = 200) -> list[dict[str, Any]]:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
        info = safe(lambda: p.info)
        if not info:
            continue
        mem = info.get("memory_info")
        procs.append({
            "pid": info.get("pid"),
            "name": info.get("name"),
            "status": info.get("status"),
            "cpu_percent": info.get("cpu_percent"),
            "memory_rss_bytes": getattr(mem, "rss", None) if mem else None,
        })
    procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
    return procs[:limit]


def scan_listening_ports() -> list[dict[str, Any]]:
    ports = []
    for conn in safe(lambda: psutil.net_connections(kind="inet"), []) or []:
        if conn.status != psutil.CONN_LISTEN:
            continue
        proc_name = None
        if conn.pid:
            proc_name = safe(lambda: psutil.Process(conn.pid).name())
        ports.append({
            "port": conn.laddr.port if conn.laddr else None,
            "address": conn.laddr.ip if conn.laddr else None,
            "pid": conn.pid,
            "process_name": proc_name,
        })
    return ports


def scan_docker_containers() -> list[dict[str, Any]]:
    if not command_exists("docker"):
        return []
    out = run_cmd(["docker", "ps", "-a", "--format", "{{json .}}"])
    if not out:
        return []
    containers = []
    for line in out.splitlines():
        parsed = safe(lambda: json.loads(line))
        if parsed:
            containers.append(parsed)
    return containers


def scan_docker_compose_projects() -> list[dict[str, Any]]:
    if not command_exists("docker"):
        return []
    out = run_cmd(["docker", "compose", "ls", "--format", "json"])
    if not out:
        return []
    parsed = safe(lambda: json.loads(out))
    return parsed if isinstance(parsed, list) else []


def scan_services() -> dict[str, Any]:
    return {
        "processes": scan_processes(),
        "listening_ports": scan_listening_ports(),
        "docker_containers": scan_docker_containers(),
        "docker_compose_projects": scan_docker_compose_projects(),
    }
