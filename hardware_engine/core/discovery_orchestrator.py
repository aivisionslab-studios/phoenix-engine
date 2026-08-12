"""
core/discovery_orchestrator.py
===============================
Orquestrador interno de descoberta contínua e ampla (hardware + SO +
ambiente de IA + serviços + inventário + modelos) — o "Telemetry" da
arquitetura descrita no documento do AHDC. Renomeado internamente para
`DiscoveryOrchestrator` (em vez de `Telemetry`) para não colidir, em
nome, com o pacote `hardware_engine.telemetry`, que agora existe como
componente separado e mais estrito, expondo `HardwareTelemetryCore`
(escopo: saúde/desempenho de hardware ao longo do tempo, pedido pela
Phoenix). Este orquestrador continua responsável pelo escopo AMPLO do
AHDC; `HardwareTelemetryCore` cobre o subconjunto "hardware telemetry"
descrito na especificação da Phoenix.

Responsabilidade única: observar continuamente o estado da máquina e
persistir os fatos. Este módulo:

  - NUNCA instala programas
  - NUNCA altera configurações
  - NUNCA executa reparos
  - NUNCA toma decisões
  - NUNCA executa benchmark por conta própria (apenas ingere resultados
    produzidos externamente pelo Benchmark Core)
  - NUNCA cria Machine Identity ou Hardware Hash (isso é de outro
    componente do Core, fora deste módulo)

Ele apenas observa, registra e disponibiliza os dados via `Manifest` e,
depois, via `HardwareDiscoveryCore`. Nenhuma Engine deve importar este
orquestrador diretamente — o único ponto de contato autorizado é
`hardware_engine.HardwareDiscoveryCore`.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Optional

from . import events as events_mod
from .persistence import Store
from ..scanners import (
    scan_hardware,
    scan_os_environment,
    scan_ai_environment,
    scan_services,
    scan_models,
    scan_inventory,
)


class DiscoveryOrchestrator:
    """Orquestrador de observação contínua. Somente leitura."""

    def __init__(self, db_path: str | Path = "ahdc_telemetry.sqlite3",
                 model_search_dirs: Optional[list[str]] = None,
                 scan_interval_seconds: float = 30.0,
                 model_scan_every_n_cycles: int = 10):
        self.store = Store(db_path)
        self.model_search_dirs = model_search_dirs or []
        self.scan_interval_seconds = scan_interval_seconds
        self.model_scan_every_n_cycles = model_scan_every_n_cycles

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._cycle_count = 0

        # Cache do estado anterior, usado só para gerar eventos de diff —
        # não é decisão, é constatação de mudança.
        self._prev_ai_env: Optional[list[dict[str, Any]]] = None
        self._prev_inventory: Optional[list[dict[str, Any]]] = None
        self._prev_services: Optional[dict[str, Any]] = None

    # ------------------------------------------------------------- ciclo único
    def scan_once(self, include_models: bool = True) -> dict[str, Any]:
        """Executa uma rodada completa de observação e persiste o snapshot.
        Retorna o snapshot gerado."""
        hardware = scan_hardware()
        os_environment = scan_os_environment()
        ai_environment = scan_ai_environment()
        services = scan_services()
        inventory = scan_inventory()

        models = None
        if include_models and self.model_search_dirs:
            models = scan_models(self.model_search_dirs)
            known_paths = self.store.known_model_paths()
            for m in models:
                self.store.upsert_model(
                    m["name"], m["format"], m["path"], m["size_bytes"],
                    m["modified_at"], m["content_hash"], m["kind_guess"],
                )
            for gone_event in events_mod.diff_models(known_paths, models):
                self.store.add_event(gone_event["category"], gone_event["event_type"],
                                      gone_event["message"], gone_event["payload"])
                if gone_event["event_type"] == "model_removed":
                    self.store.remove_model(gone_event["payload"]["path"])

        for tool in ai_environment:
            self.store.upsert_inventory(tool["name"], "ai_tool", tool.get("version"),
                                         tool.get("path"))
        for prog in inventory["installed_programs"]:
            self.store.upsert_inventory(prog["name"], "installed_program",
                                         prog.get("version"), None)

        for ev in events_mod.diff_ai_environment(self._prev_ai_env, ai_environment):
            self.store.add_event(ev["category"], ev["event_type"], ev["message"], ev["payload"])
        for ev in events_mod.diff_inventory(self._prev_inventory, inventory["installed_programs"]):
            self.store.add_event(ev["category"], ev["event_type"], ev["message"], ev["payload"])
        for ev in events_mod.diff_services(self._prev_services, services):
            self.store.add_event(ev["category"], ev["event_type"], ev["message"], ev["payload"])

        self._prev_ai_env = ai_environment
        self._prev_inventory = inventory["installed_programs"]
        self._prev_services = services

        snapshot = {
            "hardware": hardware,
            "os_environment": os_environment,
            "ai_environment": ai_environment,
            "services": services,
            "inventory": inventory,
            "models_scanned_this_cycle": models is not None,
        }
        self.store.save_snapshot(snapshot)
        return snapshot

    # ---------------------------------------------------------------- loop
    def _loop(self) -> None:
        self.store.add_event("telemetry", "started", "Telemetria iniciada.")
        while not self._stop_event.is_set():
            include_models = (self._cycle_count % self.model_scan_every_n_cycles == 0)
            try:
                self.scan_once(include_models=include_models)
            except Exception as exc:  # a Telemetria nunca pode derrubar o processo
                self.store.add_event("telemetry", "scan_error",
                                      f"Erro durante ciclo de coleta: {exc}")
            self._cycle_count += 1
            self._stop_event.wait(self.scan_interval_seconds)
        self.store.add_event("telemetry", "stopped", "Telemetria encerrada.")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="hardware-engine-discovery-orchestrator")
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    # ------------------------------------------------------- ingestão externa
    def ingest_benchmark_result(self, tool: Optional[str], model: Optional[str],
                                 metric: str, value: Optional[float],
                                 payload: Optional[dict[str, Any]] = None) -> None:
        """A Telemetria NUNCA executa benchmark. Ela apenas registra
        resultados que o Benchmark Core já produziu."""
        self.store.add_benchmark_result(tool, model, metric, value, payload)

    # ------------------------------------------------------------- consultas
    def latest_snapshot(self) -> Optional[dict[str, Any]]:
        return self.store.latest_snapshot()

    def get_events(self, since: Optional[float] = None,
                   category: Optional[str] = None) -> list[dict[str, Any]]:
        return self.store.get_events(since=since, category=category)

    def get_inventory(self, kind: Optional[str] = None) -> list[dict[str, Any]]:
        return self.store.get_inventory(kind=kind)

    def get_models(self) -> list[dict[str, Any]]:
        return self.store.get_models()

    def get_benchmark_results(self, tool: Optional[str] = None) -> list[dict[str, Any]]:
        return self.store.get_benchmark_results(tool=tool)
