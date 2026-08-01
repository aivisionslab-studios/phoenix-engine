import logging
from .models import Mission, MissionStep
from .enums import MissionAction

logger = logging.getLogger(__name__)

class MissionPlanner:
    def _step(self, action: MissionAction, target: str, description: str, **parameters) -> dict:
        return {"action": action, "target": target, "description": description, "parameters": parameters}

    def create(self, intent: str) -> Mission:
        logger.info(f"MissionPlanner: Criando missão para '{intent}'")
        raw_steps = []
        if "ollama" in intent.lower() or "chat" in intent.lower():
            raw_steps.append(self._step(MissionAction.INSTALL_PACKAGE, "ollama", "Subir container do Ollama", provider="docker"))
        elif "image" in intent.lower() or "comfyui" in intent.lower():
            raw_steps.append(self._step(MissionAction.INSTALL_PACKAGE, "comfyui", "Clonar repositório do ComfyUI", provider="git"))
        else:
            raw_steps.append(self._step(MissionAction.VALIDATE, "environment", "Validar ambiente"))
            
        steps = [MissionStep(step=i + 1, action=s["action"], target=s["target"], description=s["description"], parameters=s.get("parameters", {})) for i, s in enumerate(raw_steps)]
        return Mission(intent=intent, steps=steps)
