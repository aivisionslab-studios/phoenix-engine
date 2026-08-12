import asyncio
import logging
from dataclasses import asdict

logger = logging.getLogger(__name__)

class StateEngine:
    def __init__(self, budget, telemetry, services, models):
        self.budget = budget
        self.telemetry = telemetry
        self.services = services
        self.models = models
        self.machine_context = None
        self.hardware_data = None
        # PHX-NEW (integração AHDE, Fase 2): setado via set_ahde() depois
        # que o kernel instancia o AHDE - não é passado no construtor pra
        # não precisar reordenar a Composition Root do kernel.py.
        self.ahde = None

    def set_context(self, machine_context, hardware_data):
        self.machine_context = machine_context
        self.hardware_data = hardware_data

    def set_ahde(self, ahde) -> None:
        self.ahde = ahde

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
            "score": budget_data.get("score", 0),
            "ahde": self._get_ahde_section(),
        }

    def _get_ahde_section(self) -> dict:
        """
        PHX-NEW (integração AHDE, Fase 2): expõe só dado real, derivado
        de scan de verdade (CapabilitySnapshot vem de CapabilityEngine.
        extract() rodando em cima do hardware/services reais coletados
        no boot + a cada tick de telemetria).

        DELIBERADAMENTE NÃO expõe health_score: HealthEngine.evaluate()
        (phoenix_kernel/ahde/health/engine.py) ainda é stub fixo em 100 -
        a Fase 4 (Health real + testes de degradação) não começou. O
        próprio código da Fase 0 já documenta isso como "Regra absoluta
        #2": nenhum consumidor pode tomar decisão (nem mostrar na tela
        como se fosse calculado) com esse valor do jeito que está hoje.
        Quando a Fase 4 entregar o cálculo de verdade, aí sim isso entra
        aqui.
        """
        if self.ahde is None:
            return {"available": False}

        hw_snap = self.ahde.get_latest_hardware_snapshot()
        tel_snap = self.ahde.get_latest_telemetry_snapshot()

        return {
            "available": True,
            "capabilities": asdict(hw_snap.capabilities) if hw_snap else None,
            "hardware_snapshot_id": hw_snap.snapshot_id if hw_snap else None,
            "hardware_snapshot_at": hw_snap.timestamp if hw_snap else None,
            "last_telemetry_change_at": tel_snap.timestamp if tel_snap else None,
        }
