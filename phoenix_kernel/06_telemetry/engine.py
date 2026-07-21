import asyncio
import psutil
import logging
from typing import Any
from .interfaces import ITelemetryService
# O import mudou de engines.hardware.telemetry.core para .core (mesma pasta)
from .core import get_gpu_sensors

logger = logging.getLogger(__name__)

class TelemetryEngine(ITelemetryService):
    def __init__(self):
        pass

    async def get_live_metrics(self) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        
        # CPU e RAM em thread separada
        def get_psutil_metrics():
            cpu_usage = psutil.cpu_percent(interval=None)
            ram_usage = psutil.virtual_memory()
            return {
                "cpu_usage": cpu_usage,
                "ram_used_mb": int(ram_usage.used / (1024 * 1024)),
                "ram_total_mb": int(ram_usage.total / (1024 * 1024))
            }
        metrics = await loop.run_in_executor(None, get_psutil_metrics)
        
        # GPU (via LibreHardwareMonitor - agora lendo do próprio módulo do Kernel)
        gpu_sensors = {}
        try:
            gpu_sensors = await loop.run_in_executor(None, get_gpu_sensors)
            metrics.update({
                "gpu_temp": gpu_sensors.get("temperature_celsius"),
                "gpu_load": gpu_sensors.get("load_percent"),
                "gpu_vram_used": gpu_sensors.get("vram_used_mb")
            })
        except Exception as e:
            logger.debug(f"Telemetry: GPU sensors indisponíveis - {e}")
            metrics.update({
                "gpu_temp": None,
                "gpu_load": None,
                "gpu_vram_used": None
            })

        return metrics