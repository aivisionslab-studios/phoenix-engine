"""
telemetry/change_detection.py
==============================
Change Detection Engine + Event Publisher (especificação "Hardware
Telemetry Core v2.0").

Responsabilidade ÚNICA: comparar duas amostras consecutivas e publicar
FATOS objetivos sobre o que mudou. Nunca interpreta o significado da
mudança (isso é responsabilidade do Rules Engine / Decision Engine na
Phoenix).

Exemplo do que este módulo faz:
    gpu.temperature.changed  {old: 72, new: 79, delta: 7}

Exemplo do que este módulo NUNCA faz:
    GPU_OVERHEATING
    "Não é recomendado iniciar FLUX agora"
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from ..models.schemas import TelemetryEvent


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Métricas monitoradas para detecção de mudança, e o "domínio.métrica"
# factual correspondente ao nome do evento publicado. Threshold é a
# variação mínima (absoluta) para considerar "mudou" - evita publicar
# um evento a cada 0.01°C de ruído de sensor. Isso NÃO é uma
# interpretação de severidade, é só um filtro de ruído de leitura.
_NOISE_THRESHOLDS = {
    "cpu_temperature_celsius": 1.0,
    "gpu_temperature_celsius": 1.0,
    "vram_used_mb": 64,
    "ram_used_mb": 64,
    "disk_health_status": None,   # comparação exata (string), sem threshold numérico
    "driver_change_detected": None,  # comparação booleana
}

_EVENT_NAME_MAP = {
    "cpu_temperature_celsius": "cpu.temperature.changed",
    "gpu_temperature_celsius": "gpu.temperature.changed",
    "vram_used_mb": "gpu.vram.changed",
    "ram_used_mb": "memory.used.changed",
    "disk_health_status": "storage.health.changed",
    "driver_change_detected": "driver.changed",
    "throttling_detected": "cpu.throttling.changed",
}


class ChangeDetectionEngine:
    """Compara a amostra atual com a anterior e retorna uma lista de
    `TelemetryEvent` factuais para toda métrica que mudou além do
    limiar de ruído. Não decide nada sobre o que os eventos significam."""

    def __init__(self) -> None:
        self._previous: Optional[dict[str, Any]] = None

    def detect(self, sample_dict: dict[str, Any]) -> list[TelemetryEvent]:
        events: list[TelemetryEvent] = []
        if self._previous is None:
            self._previous = sample_dict
            return events  # primeira amostra: nada para comparar ainda

        for field_name, event_name in _EVENT_NAME_MAP.items():
            old_value = self._previous.get(field_name)
            new_value = sample_dict.get(field_name)

            if old_value is None and new_value is None:
                continue

            threshold = _NOISE_THRESHOLDS.get(field_name)
            if threshold is not None and isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                if abs(new_value - old_value) < threshold:
                    continue
                delta = new_value - old_value
            else:
                if old_value == new_value:
                    continue
                delta = None

            events.append(TelemetryEvent(
                name=event_name,
                timestamp=_now_iso(),
                old_value=old_value,
                new_value=new_value,
                delta=delta,
            ))

        self._previous = sample_dict
        return events


class EventPublisher:
    """Publica eventos factuais para quem estiver inscrito (padrão
    pub/sub simples). Mantém também um histórico em memória, consultável
    via `get_events()`. Não filtra por relevância nem prioriza nada -
    isso seria julgamento, fora do escopo deste módulo."""

    def __init__(self) -> None:
        self._subscribers: list[Callable[[TelemetryEvent], None]] = []
        self._history: list[TelemetryEvent] = []

    def subscribe(self, callback: Callable[[TelemetryEvent], None]) -> None:
        """Registra um callback que será chamado a cada evento publicado.
        Tipicamente usado pelo Rules Engine da Phoenix para reagir a
        mudanças em tempo real, sem precisar fazer polling."""
        self._subscribers.append(callback)

    def publish(self, event: TelemetryEvent) -> None:
        self._history.append(event)
        for callback in self._subscribers:
            callback(event)

    def publish_many(self, events: list[TelemetryEvent]) -> None:
        for event in events:
            self.publish(event)

    def get_events(self, since: Optional[str] = None, name: Optional[str] = None) -> list[TelemetryEvent]:
        """Histórico de eventos publicados. `since` filtra por timestamp
        ISO 8601 (>=); `name` filtra pelo nome exato do evento
        (ex.: 'gpu.temperature.changed')."""
        result = self._history
        if since is not None:
            result = [e for e in result if e.timestamp >= since]
        if name is not None:
            result = [e for e in result if e.name == name]
        return list(result)
