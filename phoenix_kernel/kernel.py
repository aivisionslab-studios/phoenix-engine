import asyncio
import importlib
import logging
from core.events.bus import EventBus
from core.kernel.kernel import PlatformKernel
from core.domain.machine import MachineContext
from phoenix_kernel.state import StateEngine
from phoenix_kernel.cloud_sync import FirestoreSync

logger = logging.getLogger(__name__)

# Intervalo do loop automático do Resident Manager (análise sozinha em
# background, sem precisar digitar "manager analyze" no terminal).
RESIDENT_LOOP_INTERVAL_SEC = 300

# Intervalo do loop de sincronização com o Firestore (só roda de verdade se
# o usuário já deu consentimento — ver phoenix_kernel/cloud_sync.py).
CLOUD_SYNC_INTERVAL_SEC = 1800

class PhoenixKernel:
    def __init__(self):
        self.event_bus = EventBus()
        self.platform_kernel = PlatformKernel()
        
        discovery_module = importlib.import_module("phoenix_kernel.01_discovery.engine")
        self.discovery = discovery_module.DiscoveryEngine()

        budget_module = importlib.import_module("phoenix_kernel.02_budget.engine")
        self.budget = budget_module.BudgetEngine()

        telemetry_module = importlib.import_module("phoenix_kernel.06_telemetry.engine")
        self.telemetry = telemetry_module.TelemetryEngine()

        services_module = importlib.import_module("phoenix_kernel.07_services.engine")
        self.services = services_module.ServicesEngine()

        models_module = importlib.import_module("phoenix_kernel.08_models.engine")
        self.models = models_module.ModelsEngine()

        planner_module = importlib.import_module("phoenix_kernel.03_planner.engine")
        self.planner = planner_module.PlannerEngine(self.event_bus, self.platform_kernel)
        self.models.set_knowledge_engine(self.planner.knowledge)

        runtime_module = importlib.import_module("phoenix_kernel.04_runtime.engine")
        self.runtime = runtime_module.RuntimeEngine(self.event_bus, self.platform_kernel)

        validation_module = importlib.import_module("phoenix_kernel.05_validation.engine")
        self.validation = validation_module.ValidationEngine()

        logs_module = importlib.import_module("phoenix_kernel.11_logs.engine")
        self.logs = logs_module.LogsEngine()

        security_module = importlib.import_module("phoenix_kernel.12_security.engine")
        self.security = security_module.SecurityEngine()

        api_module = importlib.import_module("phoenix_kernel.09_api.engine")
        
        self.state = StateEngine(self.budget, self.telemetry, self.services, self.models)
        
        # NOVO: Instancia a Camada de Inteligência
        resident_module = importlib.import_module("phoenix_kernel.intelligence.resident_manager")
        self.resident = resident_module.ResidentManager(self.state, self.planner)
        
        self.api = api_module.ApiEngine(self.state, self.models, self.planner, self.runtime, self.services, self.logs, self.validation, self.security, self.resident)
        
        self.machine_context = None
        self._resident_task = None
        self._cloud_sync_task = None
        self.cloud_sync = FirestoreSync()

    async def boot(self):
        print("[Kernel] Inicializando Discovery (Serviço 01)...")
        hw_data = await self.discovery.discover_hardware()
        
        class Profile: pass
        profile = Profile()
        profile.cpu = hw_data['cpu']
        profile.memory = hw_data['memory']
        profile.gpus = hw_data['gpus']
        profile.available_backends = hw_data['available_backends']
        
        self.machine_context = MachineContext(profile=profile)
        
        self.state.set_context(self.machine_context, hw_data)
        self.api.set_context(self.machine_context)
        
        self.logs.add_event("INFO", "Kernel", "Boot sequence initiated.")
        
        print("[Kernel] Inicializando Planner e RAG (Serviço 03)...")
        await self.planner.initialize()
        self.planner.set_context(self.machine_context)
        
        print("[Kernel] Inicializando Runtime (Serviço 04)...")
        await self.runtime.initialize()
        self.logs.add_event("INFO", "Kernel", "Phoenix Kernel Pronto.")

        print(f"[Kernel] Iniciando Resident Manager em loop automático (a cada {RESIDENT_LOOP_INTERVAL_SEC}s)...")
        self._resident_task = asyncio.create_task(self._resident_loop())

        print(f"[Kernel] Iniciando loop de sincronização com o Firestore (a cada {CLOUD_SYNC_INTERVAL_SEC}s, só se consentido)...")
        self._cloud_sync_task = asyncio.create_task(self._cloud_sync_loop())

    async def _cloud_sync_loop(self):
        """Sobe o conteúdo do RAG local (knowledge_base.json inteiro,
        incluindo benchmarks) pro Firestore, de tempos em tempos — mas
        cloud_sync.sync() já devolve 0 sem fazer nada se o usuário não
        tiver dado consentimento (ver /api/telemetry/consent no
        api_server.py), então essa task pode ficar sempre rodando sem
        risco de vazar dado sem autorização."""
        while True:
            try:
                await asyncio.sleep(CLOUD_SYNC_INTERVAL_SEC)
                machine_id = self.discovery.get_machine_id()
                sent = await self.cloud_sync.sync(machine_id)
                if sent:
                    self.logs.add_event("INFO", "FirestoreSync", f"{sent} documento(s) sincronizado(s) com o Firestore.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"FirestoreSync: falha no loop de sync - {e}")
                self.logs.add_event("ERROR", "FirestoreSync", f"Falha ao sincronizar com o Firestore: {e}")

    async def _resident_loop(self):
        """Roda analyze_machine() sozinho em background, sem precisar do
        comando manual 'manager analyze'. Só loga algo quando há alerta de
        sensor (pra não poluir o log a cada 5 min sem motivo); erros de uma
        rodada não derrubam o loop, só ficam registrados e ele tenta de novo
        na próxima."""
        while True:
            try:
                await asyncio.sleep(RESIDENT_LOOP_INTERVAL_SEC)
                report = await self.resident.analyze_machine()
                if "ALERTAS DE SENSOR" in report:
                    self.logs.add_event("WARNING", "ResidentManager", "Análise automática encontrou sensor(es) fora da faixa normal. Rode 'manager analyze' pra ver o relatório completo.")
                else:
                    self.logs.add_event("INFO", "ResidentManager", "Análise automática concluída, nada fora do normal.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"ResidentManager: falha na análise automática - {e}")
                self.logs.add_event("ERROR", "ResidentManager", f"Falha na análise automática: {e}")

    async def shutdown(self):
        print("[Kernel] Desligando serviços...")
        self.logs.add_event("INFO", "Kernel", "Shutdown initiated.")
        if self._resident_task:
            self._resident_task.cancel()
        if self._cloud_sync_task:
            self._cloud_sync_task.cancel()
        try: await self.runtime.shutdown()
        except: pass
