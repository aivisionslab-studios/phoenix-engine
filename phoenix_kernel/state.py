import asyncio
import logging

logger = logging.getLogger(__name__)

class StateEngine:
    def __init__(self, budget, telemetry, services, models):
        self.budget = budget
        self.telemetry = telemetry
        self.services = services
        self.models = models
        self.machine_context = None
        self.hardware_data = None

    def set_context(self, machine_context, hardware_data):
        self.machine_context = machine_context
        self.hardware_data = hardware_data

    async def get_state(self) -> dict:
        if not self.machine_context:
            return {"error": "Hardware ainda não descoberto"}
        
        profile = self.machine_context.profile
        gpu = profile.gpus[0] if profile.gpus else {}
        
        budget_task = self.budget.evaluate_machine(self.hardware_data)
        telemetry_task = self.telemetry.get_live_metrics()
        env_task = self.services.get_environment_status()
        models_task = self.models.get_model_and_rag_status()
        
        budget_data, telemetry_data, env, models_data = await asyncio.gather(
            budget_task, telemetry_task, env_task, models_task
        )

        return {
            "hardware": {
                "cpu": profile.cpu.get('model', 'Unknown'),
                "ram_mb": profile.memory.get('total_mb', 0),
                "gpu": gpu.get('model', 'Unknown'),
                "vram_mb": gpu.get('vram_mb', 0),
                "backends": list(profile.available_backends)
            },
            "hardware_devices": self.hardware_data,
            "budget": budget_data,
            "telemetry": telemetry_data,
            "environment": env,
            "models": models_data.get("models", []),
            "rag_docs": models_data.get("rag_docs", 0),
            "score": budget_data.get("score", 0) 
        }
