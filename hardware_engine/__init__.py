"""
hardware_engine
================
AIVisions Hardware Discovery Core (AHDC).

Duas classes públicas, dois escopos diferentes e complementares:

  - `HardwareDiscoveryCore`: descoberta ampla (hardware, SO, ambiente de
    IA, serviços, inventário, modelos), persistida continuamente em
    SQLite. É o componente que a Phoenix já integra para
    `collect_environment()` e afins.

  - `HardwareTelemetryCore`: escopo estrito de "telemetria de hardware"
    pedido pela Phoenix em 06_spec_telemetry_core_para_ahde.md —
    temperatura de CPU/GPU, uso de VRAM/RAM, saúde de disco,
    throttling, uptime e mudanças de driver, ao longo do tempo, com
    export/load em JSON e consulta de tendência (`get_trend`).

Nenhuma das duas classes decide nada. As duas só observam, registram e
disponibilizam dados — quem decide é a Phoenix (RulesEngine e afins).

Instalação como pacote pip (nunca como pasta solta com sys.path manual):

    pip install -e caminho/para/hardware_engine
"""

from .core.discovery_core import HardwareDiscoveryCore
from .telemetry.telemetry_core import HardwareTelemetryCore
from .models.schemas import TelemetrySample, TelemetryEvent

__all__ = [
    "HardwareDiscoveryCore",
    "HardwareTelemetryCore",
    "TelemetrySample",
    "TelemetryEvent",
    "__version__",
]

__version__ = "0.2.0"
CORE_VERSION = __version__
