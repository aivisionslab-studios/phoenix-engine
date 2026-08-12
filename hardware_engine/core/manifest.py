"""
manifest.py
===========
O Manifest é a "fotografia oficial" da máquina: uma visão consolidada e
estável do último estado observado pela Telemetria, mais os dados
persistentes de inventário e modelos. Nenhuma Engine pode gerar seu
próprio Manifest — este é o único ponto de verdade, e ele só existe
porque a Telemetria o alimenta continuamente.

O Manifest não observa nada por conta própria: ele é sempre uma
projeção do que já está no `Store`.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from .discovery_orchestrator import DiscoveryOrchestrator


class Manifest:
    def __init__(self, telemetry: DiscoveryOrchestrator):
        self._telemetry = telemetry

    def get(self) -> dict[str, Any]:
        """Retorna o Manifest atual: último snapshot de hardware/SO/serviços
        + inventário e modelos persistidos + eventos recentes."""
        snapshot = self._telemetry.latest_snapshot() or {}
        return {
            "generated_at": time.time(),
            "snapshot_timestamp": snapshot.get("_snapshot_timestamp"),
            "hardware": snapshot.get("hardware"),
            "os_environment": snapshot.get("os_environment"),
            "ai_environment": snapshot.get("ai_environment"),
            "services": snapshot.get("services"),
            "inventory": {
                "ai_tools": self._telemetry.get_inventory(kind="ai_tool"),
                "installed_programs": self._telemetry.get_inventory(kind="installed_program"),
            },
            "models": self._telemetry.get_models(),
            "recent_events": self._telemetry.get_events(limit=50) if False else
                             self._telemetry.get_events(),
        }

    def summary(self) -> dict[str, Any]:
        """Versão resumida do Manifest — pensada para exibição rápida
        (ex.: painel do Phoenix), sem o volume completo de processos/eventos."""
        full = self.get()
        hw = full.get("hardware") or {}
        cpu = hw.get("cpu") or {}
        mem = (hw.get("memory") or {}).get("ram") or {}
        gpus = hw.get("gpu") or []
        return {
            "generated_at": full["generated_at"],
            "cpu_utilization_percent": cpu.get("utilization_percent"),
            "ram_percent_used": mem.get("percent_used"),
            "gpu_count": len(gpus),
            "gpu_names": [g.get("name") for g in gpus if g.get("name")],
            "os": (full.get("os_environment") or {}).get("os"),
            "ai_tools_detected": [t.get("name") for t in (full.get("ai_environment") or [])],
            "models_count": len(full.get("models") or []),
            "docker_containers_count": len(
                (full.get("services") or {}).get("docker_containers", [])
            ),
        }
