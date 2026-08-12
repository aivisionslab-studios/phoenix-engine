"""
models/schemas.py
==================
Schemas de dados do Hardware Discovery Core / Telemetry.

`TelemetrySample` segue exatamente os campos pedidos na especificação
da Phoenix (06_spec_telemetry_core_para_ahde.md, seção 3), na mesma
ordem, para que o mapeamento no `HardwareDiscoveryAdapter` seja
trivial. Os campos extras abaixo do marcador `--- extras ---` NÃO
fazem parte do contrato mínimo pedido; existem porque o escopo de
"telemetria de hardware" descrito no documento de arquitetura do AHDC
(uptime da máquina, mudanças de driver) pede um pouco mais do que o
mínimo. Se a Phoenix não quiser consumi-los agora, o adapter pode
simplesmente ignorá-los — são todos opcionais.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class TelemetrySample:
    timestamp: str                      # ISO 8601, igual ao resto do Core
    cpu_temperature_celsius: Optional[float] = None
    gpu_temperature_celsius: Optional[float] = None
    vram_used_mb: Optional[int] = None
    ram_used_mb: Optional[int] = None
    disk_health_status: Optional[str] = None   # espelha o campo health_status
                                                # de scan_storage() em scanners/hardware.py
    throttling_detected: Optional[bool] = False

    # --- extras (fora do mínimo pedido, mas dentro do escopo "hardware
    # telemetry" descrito no doc de arquitetura AHDC) ---
    uptime_seconds: Optional[float] = None
    driver_change_detected: bool = False
    source_notes: dict[str, Any] = field(default_factory=dict)
    # source_notes documenta, campo a campo, de onde veio o dado (ex.:
    # {"gpu_temperature_celsius": "rocm-smi"} ou {"disk_health_status": None}
    # quando nenhuma fonte respondeu). Não é dado de telemetria em si —
    # é honestidade sobre a origem do dado, no mesmo espírito do campo
    # `source` já usado em scan_gpu().

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TelemetrySample":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class TelemetryEvent:
    """Evento FACTUAL publicado pelo Change Detection Engine/Event
    Publisher. Descreve uma mudança observada, nunca uma conclusão ou
    recomendação (ver especificação 'Hardware Telemetry Core v2.0').

    Nome do evento segue o padrão 'dominio.metrica.mudanca', ex.:
    'gpu.temperature.changed', 'driver.version.changed',
    'storage.device.added'. NUNCA um rótulo interpretativo como
    'GPU_OVERHEATING' - isso seria decisão, que pertence ao Rules
    Engine/Decision Engine da Phoenix, nunca a este modulo.
    """

    name: str                # ex: "gpu.temperature.changed"
    timestamp: str           # ISO 8601
    old_value: Any = None
    new_value: Any = None
    delta: Any = None        # new_value - old_value quando numerico; None caso contrario
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TelemetryEvent":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})
