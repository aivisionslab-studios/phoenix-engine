import logging
from core.domain.machine import MachineContext
from core.domain.execution import ExecutionPlan
from .interfaces import IPlannerService
from .knowledge_engine import KnowledgeEngine
from .evaluator import RuleEvaluator

logger = logging.getLogger(__name__)

class PlannerEngine(IPlannerService):
    def __init__(self, event_bus, kernel):
        self.knowledge = KnowledgeEngine(event_bus, kernel)
        self.evaluator = RuleEvaluator(self.knowledge)
        self.machine_context = None

    def set_context(self, context):
        self.machine_context = context

    async def initialize(self):
        await self.knowledge.initialize()

    async def plan_inference(self, context, user_prompt: str) -> ExecutionPlan:
        return await self.evaluator.evaluate(context, user_prompt=user_prompt)

    async def resolve_package(self, pkg: dict) -> dict:
        """A mágica da App Store: adapta o pacote ao hardware real."""
        if not pkg: return None
        resolved = pkg.copy()
        models = []
        
        if self.machine_context and self.machine_context.profile:
            vram = self.machine_context.profile.gpus[0].get('vram_mb', 0) if self.machine_context.profile.gpus else 0
            ram = self.machine_context.profile.memory.get('total_mb', 0)
            package_id = pkg.get("id", "")
            
            if package_id == "chat":
                if ram >= 16000 and vram >= 4000:
                    models = ["Qwen3 8B", "Gemma3 4B"]
                else:
                    models = ["Qwen3 1.5B", "Phi-4 Mini"]
            elif package_id == "image":
                if vram >= 8000:
                    models = ["Flux.1", "SDXL 1.0"]
                else:
                    models = ["SD 1.5 (DreamShaper)"]
            else:
                models = ["Definido pelo Setup"]
                
        resolved["resolved_models"] = models
        return resolved