import logging
from .interfaces import IApiService

logger = logging.getLogger(__name__)

class ApiEngine(IApiService):
    def __init__(self, state_engine, models_engine, planner_engine, runtime_engine, services_engine, logs_engine, validation_engine, security_engine, resident_manager):
        self.state = state_engine
        self.models = models_engine
        self.planner = planner_engine
        self.runtime = runtime_engine
        self.services = services_engine
        self.logs = logs_engine
        self.validation = validation_engine
        self.security = security_engine
        self.resident = resident_manager
        self.machine_context = None

    def set_context(self, machine_context):
        self.machine_context = machine_context

    async def process_command(self, cmd: str) -> dict:
        if not cmd: return {"output": "Comando vazio."}

        cmd_lower = cmd.lower()

        if cmd_lower == "help":
            return {"output": "Comandos disponíveis:\n- help\n- status\n- models\n- infer [pergunta]\n- install list\n- install service [nome]\n- install package [nome]\n- logs\n- validate\n- security\n- manager analyze"}
        
        if cmd_lower == "manager analyze":
            self.logs.add_event("INFO", "API", "Resident Manager solicitado para análise.")
            report = await self.resident.analyze_machine()
            return {"output": report}

        if cmd_lower == "status":
            state = await self.state.get_state()
            if "error" in state: return {"output": "Aguardando descoberta de hardware..."}
            t = state['telemetry']
            return {"output": f"CPU: {t['cpu_usage']}% | RAM: {t['ram_used_mb']}MB\nGPU: {state['hardware']['gpu']} | Temp: {t['gpu_temp']}°C"}

        if cmd_lower == "models":
            models_data = await self.models.get_model_and_rag_status()
            return {"output": "Modelos Ollama disponíveis:\n" + "\n".join(models_data.get("models", []))}

        if cmd_lower.startswith("install "):
            args = cmd[8:].strip().split(" ", 1)
            if not args[0]: return {"output": "Uso: install list\n- install service [nome]\n- install package [nome]"}
            action = args[0].lower()
            if action == "list":
                self.logs.add_event("INFO", "API", "Listando pacotes.")
                return {"output": "AIVisions Packages Catalog:\n" + self.services.packages.list_packages()}
            if len(args) < 2: return {"output": "Uso: install service [nome] ou install package [nome]"}
            target = args[1].lower()
            if action == "service":
                return {"output": await self.services.install_service(target)}
            elif action == "package":
                return {"output": await self.services.install_package(target)}
            else: return {"output": "Ação inválida."}

        if cmd_lower == "logs":
            logs = self.logs.get_recent_logs(10)
            if not logs: return {"output": "Nenhum log."}
            return {"output": "\n".join([f"[{l['timestamp']}] [{l['source']}] {l['message']}" for l in logs])}

        if cmd_lower == "validate":
            val_data = await self.validation.validate_system()
            return {"output": f"Validation Status: {val_data.get('status')}\nDetails: {val_data.get('checks')}"}

        if cmd_lower == "security":
            sec_data = await self.security.check_integrity()
            return {"output": f"Security Check:\n- Admin: {sec_data.get('is_admin')}\n- Firewall: {sec_data.get('firewall_status')}"}

        if cmd_lower.startswith("infer "):
            prompt = cmd[6:]
            try:
                plan = await self.planner.plan_inference(self.machine_context, user_prompt=prompt)
                result = await self.runtime.execute(plan)
                if result.status.value == "success": return {"output": f"Modelo: {plan.model}\n--- Resultado ---\n{result.output}"}
                else: return {"output": f"[ERRO] {result.errors}"}
            except Exception as e: return {"output": f"[ERRO] {str(e)}"}

        return {"output": "Comando não reconhecido. Digite 'help'."}
