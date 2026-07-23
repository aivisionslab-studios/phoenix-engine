
import psutil
from .base import ITelemetryProvider
from phoenix_kernel.shared.models import TelemetrySnapshot

class LinuxTelemetryProvider(ITelemetryProvider):
    def get_metrics(self) -> TelemetrySnapshot:
        cpu_usage = psutil.cpu_percent(interval=None)
        ram_usage = psutil.virtual_memory()
        return TelemetrySnapshot(
            cpu_usage_percent=cpu_usage,
            ram_used_mb=int(ram_usage.used / (1024 * 1024)),
            gpu_temp_celsius=None,
            gpu_load_percent=None,
            gpu_vram_used_mb=None
        )
