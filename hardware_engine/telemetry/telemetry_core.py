"""
telemetry/telemetry_core.py
============================
`HardwareTelemetryCore` — implementação do contrato pedido pela Phoenix
em 06_spec_telemetry_core_para_ahde.md.

Escopo estrito (o que ESTE módulo coleta):
    - Temperatura de CPU/GPU ao longo do tempo
    - Uso de VRAM/RAM ao longo de uma sessão ou entre sessões
    - Saúde de disco (SMART status, degradação)
    - Throttling detectado (heurística best-effort, ver scanners/hardware.py)
    - Uptime da máquina
    - Mudanças de driver detectadas entre execuções

O que ESTE módulo explicitamente NÃO faz (fica na Phoenix, conforme a
seção "Escopo: o que NÃO é telemetria de hardware" da especificação):
    - Tempo de carregamento de um modelo específico
    - Sucesso/falha de missão (benchmark, geração de imagem etc.)
    - Eventos de orquestração (qual runtime foi escolhido, por quê)

E, como o resto do Core: NUNCA decide nada. Só observa, registra e
disponibiliza. "Reduzir carga da GPU porque está quente" é decisão —
pertence à Phoenix/RulesEngine, nunca a este módulo.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import psutil

from ..models.schemas import TelemetrySample, TelemetryEvent
from ..scanners.hardware import (
    scan_cpu,
    scan_memory,
    scan_gpu,
    scan_storage,
    detect_cpu_throttling,
)
from ..scanners.os_environment import scan_drivers
from .change_detection import ChangeDetectionEngine, EventPublisher
from .runtime_monitor import RuntimeMonitor


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HardwareTelemetryCore:
    """Coleta e persiste amostras de saúde/desempenho de hardware ao
    longo do tempo. Não decide nada — apenas observa e registra."""

    def __init__(self) -> None:
        self._samples: list[TelemetrySample] = []
        self._session_started_at: Optional[float] = None
        self._prev_driver_signature: Optional[list[str]] = None
        # Hardware Telemetry Core v2.0: Change Detection Engine + Event
        # Publisher (fatos, nunca interpretacao) e Runtime Monitor
        # (contexto de execucao de tarefas da Phoenix).
        self._change_detector = ChangeDetectionEngine()
        self._event_publisher = EventPublisher()
        self._runtime_monitor = RuntimeMonitor(sample_fn=lambda: self._collect_sample().to_dict())

    # --------------------------------------------------------------- sessão
    def start_session(self) -> None:
        """Inicia uma sessão de coleta. Chamado quando a Phoenix sobe.
        Reinicia o buffer de amostras em memória (o histórico persistido
        anteriormente, se houver, deve ser recuperado via `load()`)."""
        self._session_started_at = time.time()
        self._prev_driver_signature = self._driver_signature()

    # -------------------------------------------------------------- amostra
    def record_sample(self) -> TelemetrySample:
        """Coleta uma amostra pontual do estado atual da máquina e a
        adiciona ao histórico em memória. Chamado periodicamente pela
        Phoenix (ou internamente, em intervalo próprio, se configurado
        para isso no futuro). Também alimenta o Change Detection Engine,
        que publica eventos factuais para quem estiver inscrito via
        `subscribe()` - sem nenhuma interpretação do que a mudança
        significa."""
        sample = self._collect_sample()
        self._samples.append(sample)
        events = self._change_detector.detect(sample.to_dict())
        self._event_publisher.publish_many(events)
        return sample

    def _collect_sample(self) -> TelemetrySample:
        cpu_info = scan_cpu()
        gpus = scan_gpu()
        mem = scan_memory()
        disks = scan_storage()

        gpu_temp = None
        gpu_source = None
        vram_used_mb = None
        if gpus:
            primary = gpus[0]
            gpu_temp = primary.get("temperature_c")
            gpu_source = primary.get("source")
            vram_bytes = primary.get("vram_used_bytes")
            vram_used_mb = int(vram_bytes / (1024 * 1024)) if vram_bytes is not None else None

        ram_used_bytes = (mem.get("ram") or {}).get("used_bytes")
        ram_used_mb = int(ram_used_bytes / (1024 * 1024)) if ram_used_bytes is not None else None

        disk_health = disks[0].get("health_status") if disks else None

        driver_sig = self._driver_signature()
        driver_changed = (
            self._prev_driver_signature is not None
            and driver_sig != self._prev_driver_signature
        )
        self._prev_driver_signature = driver_sig

        uptime = None
        boot_time = self._safe_boot_time()
        if boot_time is not None:
            uptime = max(0.0, time.time() - boot_time)

        return TelemetrySample(
            timestamp=_now_iso(),
            cpu_temperature_celsius=cpu_info.get("temperature_celsius"),
            gpu_temperature_celsius=gpu_temp,
            vram_used_mb=vram_used_mb,
            ram_used_mb=ram_used_mb,
            disk_health_status=disk_health,
            throttling_detected=bool(detect_cpu_throttling(cpu_info)),
            uptime_seconds=uptime,
            driver_change_detected=driver_changed,
            source_notes={
                "gpu_temperature_celsius": gpu_source,
                "cpu_temperature_celsius": "psutil.sensors_temperatures" if cpu_info.get("temperature_celsius") is not None else None,
                "disk_health_status": "smartctl" if disk_health is not None else None,
            },
        )

    @staticmethod
    def _safe_boot_time() -> Optional[float]:
        try:
            return psutil.boot_time()
        except Exception:
            return None

    @staticmethod
    def _driver_signature() -> list[str]:
        drivers = scan_drivers()
        return sorted(drivers.get("gpu_related_modules") or [])

    # ------------------------------------------------------------- persistência
    def export_json(self, path: str | Path) -> None:
        """Persiste as amostras coletadas no disco, em JSON."""
        payload = {
            "session_started_at": self._session_started_at,
            "exported_at": time.time(),
            "samples": [s.to_dict() for s in self._samples],
        }
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def load(self, path: str | Path) -> None:
        """Carrega histórico já salvo (sem nova coleta). Substitui o
        buffer de amostras em memória pelo conteúdo do arquivo."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self._session_started_at = data.get("session_started_at")
        self._samples = [TelemetrySample.from_dict(s) for s in data.get("samples", [])]

    # ----------------------------------------------------------------- consulta
    def get_samples(self) -> list[TelemetrySample]:
        return list(self._samples)

    def get_trend(self, metric: str, window: int = 10) -> dict[str, Any]:
        """Consulta simples de tendência sobre as últimas `window`
        amostras que tiverem valor não-nulo para `metric`. Não
        interpreta nem recomenda nada — apenas reporta primeiro valor,
        último valor, variação absoluta e percentual. Quem decide o que
        fazer com isso (ex.: alertar sobre degradação) é quem consome
        o dado, nunca este módulo."""
        values = [
            (s.timestamp, getattr(s, metric, None))
            for s in self._samples
            if getattr(s, metric, None) is not None
        ]
        values = values[-window:]

        if len(values) < 2:
            return {
                "metric": metric,
                "window": window,
                "sample_count": len(values),
                "first_value": values[0][1] if values else None,
                "last_value": values[-1][1] if values else None,
                "absolute_change": None,
                "percent_change": None,
                "insufficient_data": True,
            }

        first_ts, first_val = values[0]
        last_ts, last_val = values[-1]
        absolute_change = last_val - first_val
        percent_change = (absolute_change / first_val * 100) if first_val not in (0, None) else None

        return {
            "metric": metric,
            "window": window,
            "sample_count": len(values),
            "first_value": first_val,
            "first_timestamp": first_ts,
            "last_value": last_val,
            "last_timestamp": last_ts,
            "absolute_change": absolute_change,
            "percent_change": percent_change,
            "insufficient_data": False,
        }

    # ------------------------------------------------- SDK (secao 8 da spec)
    def get_current_state(self) -> dict[str, Any]:
        """Estado mais recente observado (última amostra), ou uma
        amostra nova se ainda não houver nenhuma."""
        if self._samples:
            return self._samples[-1].to_dict()
        return self.record_sample().to_dict()

    def get_history(self, window: Optional[int] = None) -> list[dict[str, Any]]:
        """Histórico completo de amostras, ou as últimas `window` se
        especificado."""
        samples = self._samples[-window:] if window else self._samples
        return [s.to_dict() for s in samples]

    def get_runtime_metrics(self, task_name: Optional[str] = None) -> list[dict[str, Any]]:
        """Contexto de hardware ao redor de tarefas da Phoenix (ver
        Runtime Monitor). Use `start_task`/`sample_during`/`end_task`
        para alimentar isso."""
        return self._runtime_monitor.get_task_history(task_name=task_name)

    def start_task(self, task_name: str) -> None:
        self._runtime_monitor.start_task(task_name)

    def sample_during_task(self, task_name: str) -> None:
        self._runtime_monitor.sample_during(task_name)

    def end_task(self, task_name: str) -> Optional[dict[str, Any]]:
        return self._runtime_monitor.end_task(task_name)

    def get_health_metrics(self) -> dict[str, Any]:
        """Indicadores de saúde (desgaste, degradação) extraídos da
        amostra mais recente - sem nenhuma conclusão sobre se há falha
        iminente, apenas os fatos observados."""
        current = self.get_current_state()
        return {
            "disk_health_status": current.get("disk_health_status"),
            "throttling_detected": current.get("throttling_detected"),
            "driver_change_detected": current.get("driver_change_detected"),
            "uptime_seconds": current.get("uptime_seconds"),
        }

    def get_events(self, since: Optional[str] = None, name: Optional[str] = None) -> list[dict[str, Any]]:
        """Eventos factuais publicados pelo Change Detection Engine
        (ex.: 'gpu.temperature.changed'). Nunca conclusões."""
        return [e.to_dict() for e in self._event_publisher.get_events(since=since, name=name)]

    def subscribe(self, callback) -> None:
        """Registra um callback chamado a cada evento factual publicado
        (tipicamente usado pelo Rules Engine da Phoenix para reagir em
        tempo real, sem polling)."""
        self._event_publisher.subscribe(callback)
