"""
core/discovery_core.py
========================
`HardwareDiscoveryCore` — API pública ampla do Hardware Discovery Core
(descoberta de hardware/SO/ambiente de IA/serviços/inventário/modelos,
persistida continuamente). Corresponde ao componente que a Phoenix já
integra hoje para `collect_environment()` e afins.

Esta é a classe que Phoenix, AI Doctor ou qualquer Engine futura devem
importar para o escopo AMPLO. Nenhuma Engine acessa
`DiscoveryOrchestrator`, `Store` ou arquivos internos diretamente —
sempre através desta classe (ou de `HardwareTelemetryCore`, para o
escopo estrito de telemetria de hardware ao longo do tempo).

Fluxo:

    Scanners -> DiscoveryOrchestrator -> Manifest -> HardwareDiscoveryCore -> Phoenix -> Engines

Esta classe não tem lógica própria de observação: ela delega tudo para
DiscoveryOrchestrator/Manifest e apenas expõe uma interface pública
estável e documentada.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .manifest import Manifest
from .discovery_orchestrator import DiscoveryOrchestrator


class HardwareDiscoveryCore:
    """Ponto único de entrada para consumo de telemetria pelas Engines."""

    def __init__(self, db_path: str | Path = "hardware_engine_discovery.sqlite3",
                 model_search_dirs: Optional[list[str]] = None,
                 scan_interval_seconds: float = 30.0,
                 autostart: bool = True):
        self._telemetry = DiscoveryOrchestrator(
            db_path=db_path,
            model_search_dirs=model_search_dirs,
            scan_interval_seconds=scan_interval_seconds,
        )
        self._manifest = Manifest(self._telemetry)
        if autostart:
            self.start()

    # --------------------------------------------------------- ciclo de vida
    def start(self) -> None:
        """Inicia a coleta contínua em background."""
        self._telemetry.start()

    def stop(self) -> None:
        """Encerra a coleta contínua. Não apaga dados persistidos."""
        self._telemetry.stop()

    def force_scan(self) -> dict[str, Any]:
        """Força uma rodada de coleta imediata (útil para debug/CLI),
        fora do intervalo agendado. Ainda é só observação, não decisão."""
        return self._telemetry.scan_once()

    # --------------------------------------------------------- API pública
    def get_current_state(self) -> dict[str, Any]:
        """Estado atual completo da máquina (Manifest)."""
        return self._manifest.get()

    def get_system_summary(self) -> dict[str, Any]:
        """Resumo enxuto do sistema, pronto para exibição em painel."""
        return self._manifest.summary()

    def get_event_history(self, since: Optional[float] = None,
                           category: Optional[str] = None) -> list[dict[str, Any]]:
        """Histórico de eventos observados (instalação, remoção, erro,
        início/parada, mudança de estado). `since` é um timestamp unix
        opcional; `category` filtra por categoria (ex.: 'ai_environment',
        'models', 'inventory', 'services', 'telemetry')."""
        return self._telemetry.get_events(since=since, category=category)

    def get_inventory(self, kind: Optional[str] = None) -> list[dict[str, Any]]:
        """Inventário de programas/ferramentas. `kind` opcional:
        'ai_tool' ou 'installed_program'."""
        return self._telemetry.get_inventory(kind=kind)

    def get_resource_usage(self) -> dict[str, Any]:
        """Utilização atual de CPU/RAM/Swap/Disco/GPU."""
        snapshot = self._telemetry.latest_snapshot() or {}
        return snapshot.get("hardware", {})

    def get_processes(self) -> list[dict[str, Any]]:
        """Lista de processos ativos (mais recentes primeiro por uso de CPU)."""
        snapshot = self._telemetry.latest_snapshot() or {}
        return (snapshot.get("services") or {}).get("processes", [])

    def get_services(self) -> dict[str, Any]:
        """Serviços observados: processos, portas, containers e projetos
        Docker Compose."""
        snapshot = self._telemetry.latest_snapshot() or {}
        return snapshot.get("services", {})

    def get_installed_programs(self) -> list[dict[str, Any]]:
        """Programas instalados no sistema (best-effort por plataforma)."""
        snapshot = self._telemetry.latest_snapshot() or {}
        return (snapshot.get("inventory") or {}).get("installed_programs", [])

    def get_installed_models(self) -> list[dict[str, Any]]:
        """Modelos descobertos em disco (GGUF, Safetensors, LoRA, etc.)."""
        return self._telemetry.get_models()

    def get_containers(self) -> list[dict[str, Any]]:
        """Containers Docker observados."""
        snapshot = self._telemetry.latest_snapshot() or {}
        return (snapshot.get("services") or {}).get("docker_containers", [])

    def get_ai_environment(self) -> list[dict[str, Any]]:
        """Ferramentas de IA detectadas no ambiente atual."""
        snapshot = self._telemetry.latest_snapshot() or {}
        return snapshot.get("ai_environment", [])

    def get_os_environment(self) -> dict[str, Any]:
        """SO, kernel, distro, WSL, Docker e runtimes (Vulkan/CUDA/ROCm/DirectML)."""
        snapshot = self._telemetry.latest_snapshot() or {}
        return snapshot.get("os_environment", {})

    # ---------------------------------------------- ingestão de benchmark
    def ingest_benchmark_result(self, tool: Optional[str], model: Optional[str],
                                 metric: str, value: Optional[float],
                                 payload: Optional[dict[str, Any]] = None) -> None:
        """Permite que o Benchmark Core registre um resultado já produzido
        por ele. O SDK/Telemetry nunca executa o benchmark em si."""
        self._telemetry.ingest_benchmark_result(tool, model, metric, value, payload)

    def get_benchmark_results(self, tool: Optional[str] = None) -> list[dict[str, Any]]:
        """Resultados de benchmark previamente ingeridos."""
        return self._telemetry.get_benchmark_results(tool=tool)

    # --------------------------------------------------------------- extensão
    def register_ai_tool_connector(self, name: str, detector_fn) -> None:
        """Permite registrar um novo conector de detecção de ferramenta de
        IA sem modificar o núcleo do scanner (extensibilidade prevista
        na especificação)."""
        from ..scanners.ai_environment import register_connector
        register_connector(name, detector_fn)
