import logging

logger = logging.getLogger(__name__)

class ApprovalEngine:
    """Gerencia o ciclo de vida de um plano. Nada executa sem aprovação explícita."""
    def __init__(self):
        self._pending_plan = None

    def request_approval(self, plan: list, intent: str):
        if self._pending_plan is not None:
            return False # Já existe um plano aguardando
        self._pending_plan = {"intent": intent, "plan": plan}
        logger.info(f"ApprovalEngine: Plano criado e aguardando aprovação humana.")
        return True

    def get_pending(self) -> dict:
        return self._pending_plan

    def approve_and_clear(self) -> list:
        if not self._pending_plan: return []
        plan = self._pending_plan["plan"]
        self._pending_plan = None
        return plan

    def reject(self):
        self._pending_plan = None
        logger.info("ApprovalEngine: Plano rejeitado pelo usuário.")
