import asyncio
import shutil
import urllib.request
import logging
from typing import Any
from .interfaces import IServicesService
from .provisioning import ProvisioningEngine
from .package_manager import PackageManager

logger = logging.getLogger(__name__)

class ServicesEngine(IServicesService):
    def __init__(self, budget_engine=None):
        self.provisioning = ProvisioningEngine()
        self.packages = PackageManager()

    async def get_environment_status(self) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        def check():
            env = {"docker": shutil.which("docker") is not None, "python": True, "vulkan": shutil.which("vulkaninfo") is not None, "ollama": False}
            try:
                with urllib.request.urlopen("http://localhost:11434/api/version", timeout=1) as r: env["ollama"] = r.status == 200
            except: pass
            return env
        return await loop.run_in_executor(None, check)

    async def install_service(self, service_name: str) -> str:
        loop = asyncio.get_running_loop()
        # Resolve a missão e executa o provisionamento em thread isolada
        def run_service():
            resolved = (service_name, [service_name])
            return self.provisioning.execute(resolved[0], resolved[1])
        return await loop.run_in_executor(None, run_service)

    async def install_package(self, package_name: str) -> str:
        loop = asyncio.get_running_loop()
        def run_package():
            resolved = self.packages.resolve_mission(package_name)
            if not resolved: return f"[ERRO] Missão '{package_name}' não encontrada."
            pkg_name, connectors = resolved
            return self.provisioning.execute(pkg_name, connectors)
        return await loop.run_in_executor(None, run_package)
