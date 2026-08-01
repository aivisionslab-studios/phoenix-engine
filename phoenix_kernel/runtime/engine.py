from __future__ import annotations
import asyncio
import inspect
import logging
from pathlib import Path
from typing import Any

from core.contracts.engine import IEngine
from core.contracts.runtime import IRuntimeSDK
from core.domain.engine import EngineDescriptor, HealthStatus, Capability
from core.domain.execution import ExecutionPlan, ExecutionResult, ExecutionStatus
from core.domain.runtime import RuntimeDescriptor, RuntimeStatus, RuntimeState
from core.events.bus import EventBus
from core.events.base import Event
from core.kernel.kernel import PlatformKernel

# Importando os drivers da pasta local 'drivers'
# PHX-FIX: OllamaDriver removido definitivamente. O LLM roda via llama.cpp e imagens via sdxl.
from .drivers.llama_cpp import LlamaCppDriver
from .drivers.sd_cpp import SdCppDriver
from .drivers.whisper import WhisperDriver
from .drivers.piper import PiperDriver
from .drivers.comfyui import ComfyUIDriver

logger = logging.getLogger(__name__)

# Type hint genérico para evitar dependência de arquivos que possam ter ficado para trás
RuntimeDriver = Any


async def _call_driver_start(driver: RuntimeDriver, plan: ExecutionPlan | None) -> bool:
    """PHX-FIX: chama driver.start() passando `plan` SOMENTE se a assinatura aceitar."""
    sig = inspect.signature(driver.start)
    if len(sig.parameters) >= 1:
        return await driver.start(plan)
    return await driver.start()


class RuntimeEngine(IEngine, IRuntimeSDK):
    def __init__(self, event_bus: EventBus, kernel: PlatformKernel) -> None:
        self._event_bus = event_bus
        self._kernel = kernel
        self._drivers: dict[str, RuntimeDriver] = {}
        self._active_runtimes: set[str] = set()
        self._watchdog_task: asyncio.Task | None = None
        
        self._descriptor = EngineDescriptor(
            id="runtime", name="AIVisions Runtime Engine", version="3.0.0", sdk_version="1.0.0",
            capabilities=(Capability(name="execution", version="1.0"),)
        )

    @property
    def descriptor(self) -> EngineDescriptor: return self._descriptor

    async def initialize(self) -> None:
        config_eng = self._kernel.resolve("config") if hasattr(self._kernel, 'resolve') else None
        storage = self._kernel.resolve("storage") if hasattr(self._kernel, 'resolve') else None
        ws_path = await storage.get_workspace_path() if storage else Path(".")
        all_cfg = config_eng.get_all() if config_eng else {}
        
        # Backend Oficial LLM (CPU)
        self._drivers["llama.cpp"] = LlamaCppDriver()

        # CORREÇÃO: antes os 4 drivers opcionais estavam num único try -
        # se qualquer um falhasse ao instanciar, os que viriam depois dele
        # na mesma lista nunca chegavam a ser registrados (mesmo que
        # funcionassem perfeitamente sozinhos). Agora cada um é isolado -
        # uma falha em "sdxl" não impede "whisper"/"piper"/"comfyui".
        optional_drivers = [
            ("sdxl", lambda: SdCppDriver(all_cfg, ws_path)),
            ("whisper", lambda: WhisperDriver(all_cfg, ws_path)),
            ("piper", lambda: PiperDriver(all_cfg, ws_path)),
            ("comfyui", lambda: ComfyUIDriver(all_cfg)),
        ]
        for driver_name, factory in optional_drivers:
            try:
                self._drivers[driver_name] = factory()
            except Exception as e:
                logger.error(f"RuntimeEngine: Falha ao carregar driver opcional '{driver_name}': {e}", exc_info=True)
        
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())

    async def shutdown(self) -> None:
        if self._watchdog_task: self._watchdog_task.cancel()
        for runtime in list(self._active_runtimes): await self.stop(runtime)

    async def health(self) -> HealthStatus: return HealthStatus.HEALTHY

    async def list_runtimes(self) -> tuple[RuntimeDescriptor, ...]:
        descs = []
        for name in self._active_runtimes: descs.append(RuntimeDescriptor(name=name))
        return tuple(descs)

    async def start(self, runtime: str, plan: ExecutionPlan | None = None) -> bool:
        driver = self._drivers.get(runtime)
        if not driver: return False
        success = await _call_driver_start(driver, plan)
        if success:
            self._active_runtimes.add(runtime)
            if self._event_bus:
                await self._event_bus.publish(Event(event_type="runtime.started", source="runtime", payload={"runtime": runtime}))
        return success

    async def stop(self, runtime: str) -> bool:
        driver = self._drivers.get(runtime)
        if not driver: return False
        success = await driver.stop()
        if success:
            self._active_runtimes.discard(runtime)
            if self._event_bus:
                await self._event_bus.publish(Event(event_type="runtime.stopped", source="runtime", payload={"runtime": runtime}))
        return success

    async def status(self, runtime: str) -> RuntimeStatus:
        driver = self._drivers.get(runtime)
        if not driver: return RuntimeStatus(name=runtime, state=RuntimeState.ERROR)
        return await driver.status()

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        driver = self._drivers.get(plan.runtime)
        if not driver:
            return ExecutionResult(plan_id=plan.id, status=ExecutionStatus.FAILED, errors=[f"Runtime '{plan.runtime}' not found"])
        
        if plan.runtime not in self._active_runtimes:
            # PHX-FIX: passa o plan adiante para o driver saber qual modelo carregar
            started = await self.start(plan.runtime, plan)
            if not started:
                logger.warning("RuntimeEngine: Failed to start '%s'.", plan.runtime)
                # PHX-FIX: Retorna falha imediata. Não fazer fallback silencioso para Ollama.
                return ExecutionResult(
                    plan_id=plan.id, 
                    status=ExecutionStatus.FAILED, 
                    errors=[f"Failed to start runtime '{plan.runtime}'"]
                )
        
        result = await driver.execute(plan)
        if result.status != ExecutionStatus.SUCCESS:
            logger.warning(f"RuntimeEngine: Execution failed on '{plan.runtime}'. Errors: {result.errors}")
            
        # PHX-FIX: Removido o bloco de FALLBACK LOGIC para Ollama.
        # Se o motor nativo falhar, a falha deve ser explícita.
        return result

    async def pull_model(self, runtime: str, model_name: str) -> bool:
        driver = self._drivers.get(runtime)
        if not driver or not hasattr(driver, "pull_model"): return False
        if runtime not in self._active_runtimes: await self.start(runtime)
        return await driver.pull_model(model_name)

    async def embed(self, runtime: str, model: str, text: str) -> list[float]:
        driver = self._drivers.get(runtime)
        if not driver or not hasattr(driver, "embed"): return []
        if runtime not in self._active_runtimes: await self.start(runtime)
        return await driver.embed(model, text)

    async def describe_image(self, runtime: str, model: str, prompt: str, image_path: str) -> str:
        driver = self._drivers.get(runtime)
        if not driver or not hasattr(driver, "describe_image"): return "Error: Runtime does not support image description."
        if runtime not in self._active_runtimes: await self.start(runtime)
        return await driver.describe_image(model, prompt, image_path)

    async def _watchdog_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(30)
                for runtime_name in list(self._active_runtimes):
                    driver = self._drivers.get(runtime_name)
                    if not driver: continue
                    status = await driver.status()
                    if status.state != RuntimeState.RUNNING:
                        await driver.stop()
                        success = await _call_driver_start(driver, None)
                        if not success: self._active_runtimes.discard(runtime_name)
            except asyncio.CancelledError:
                break