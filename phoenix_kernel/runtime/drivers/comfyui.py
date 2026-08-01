from __future__ import annotations
import logging
from core.domain.execution import ExecutionPlan, ExecutionResult, ExecutionStatus
from core.domain.runtime import RuntimeStatus, RuntimeState

logger = logging.getLogger(__name__)

class ComfyUIDriver:
    def __init__(self, config: dict) -> None: pass
    @property
    def name(self) -> str: return "comfyui"
    async def start(self) -> bool: return True
    async def stop(self) -> bool: return True
    async def status(self) -> RuntimeStatus: return RuntimeStatus(name=self.name, state=RuntimeState.STOPPED)
    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        return ExecutionResult(plan_id=plan.id, status=ExecutionStatus.FAILED, errors=["comfyui driver not fully implemented in this build"])
