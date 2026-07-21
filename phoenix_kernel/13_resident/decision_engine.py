import logging

logger = logging.getLogger(__name__)

class DecisionEngine:
    def __init__(self, state_engine):
        self.state = state_engine

    async def create_plan(self, intent: str, research_data: dict) -> list:
        # Usa os dados da pesquisa para montar o plano
        plan = [
            {"step": 1, "action": "Validar Ambiente (Docker/Vulkan)", "tool": "validate_environment"},
            {"step": 2, "action": f"Instalar Runtime (Pesquisado: {research_data.get('software', 'N/A')})", "tool": "install_package", "target": "foundation_runtime"},
            {"step": 3, "action": "Instalar Stack de IA", "tool": "install_package", "target": "chat"}
        ]
        return plan
