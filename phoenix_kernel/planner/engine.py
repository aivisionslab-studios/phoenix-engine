import logging
from core.domain.machine import MachineContext
from core.domain.execution import ExecutionPlan
from .interfaces import IPlannerService
from .knowledge_engine import KnowledgeEngine
from .evaluator import RuleEvaluator

logger = logging.getLogger(__name__)

class PlannerEngine(IPlannerService):
    def __init__(self, event_bus, kernel):
        # Instancia o KnowledgeEngine real (ChromaDB) corretamente
        self.knowledge = KnowledgeEngine(event_bus, kernel)
        self.evaluator = RuleEvaluator(self.knowledge)
        self.machine_context = None

    def set_context(self, context):
        self.machine_context = context

    async def initialize(self):
        # O initialize do KnowledgeEngine vai tentar garantir o modelo de embedding.
        # Se não conseguir (porque o Ollama foi removido), ele loga um aviso e 
        # desativa o RAG internamente, mas NÃO QUEBRA a inicialização da Phoenix.
        await self.knowledge.initialize()

    async def plan_inference(self, context, user_prompt: str) -> ExecutionPlan:
        return await self.evaluator.evaluate(context, user_prompt=user_prompt)

    async def resolve_package(self, pkg: dict) -> dict:
        """Retorna os metadados do pacote."""
        if not pkg: return None
        resolved = pkg.copy()
        resolved["resolved_models"] = ["Ver Catálogo"]
        return resolved