import asyncio
import psutil
import logging
from typing import Any
from .interfaces import IValidationService

logger = logging.getLogger(__name__)

class ValidationEngine(IValidationService):
    def __init__(self):
        pass

    async def validate_system(self) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        
        def check():
            ram = psutil.virtual_memory()
            return {
                "ram_total_mb": int(ram.total / (1024 * 1024)),
                "cpu_cores": psutil.cpu_count(logical=False)
            }
        result = await loop.run_in_executor(None, check)
        logger.info("ValidationEngine: System validation passed.")
        return {"status": "ok", "checks": result}
