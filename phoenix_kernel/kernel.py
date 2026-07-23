import asyncio
import importlib
import logging
from core.events.bus import EventBus
from core.kernel.kernel import PlatformKernel
from core.domain.machine import MachineContext
from phoenix_kernel.state import StateEngine

logger = logging.getLogger(__name__)

# Intervalo do loop automático de sync com o Firestore. cloud_sync.sync()
# já devolve 0 sem fazer nada se não houver consentimento — essa task pode
# ficar sempre rodando sem risco de vazar dado sem autorização.
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
        
        resident_module = importlib.import_module("phoenix_kernel.intelligence.resident_manager")
        self.resident = resident_module.ResidentManager(self.state, self.planner)
        
        self.api = api_module.ApiEngine(self.state, self.models, self.planner, self.runtime, self.services, self.logs, self.validation, self.security, self.resident)
        
        self.machine_context = None
        self._cloud_sync_task = None
        
        # Seguro: se não tiver google-cloud-firestore instalado, não quebra o boot
        self.cloud_sync = None
        try:
            from phoenix_kernel.cloud_sync import FirestoreSync
            self.cloud_sync = FirestoreSync()
        except ImportError:
            logger.warning("Biblioteca google-cloud-firestore não instalada. Sincronização na nuvem desativada.")

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

        if self.cloud_sync is not None:
            print(f"[Kernel] Iniciando loop de sincronização com o Firestore (a cada {CLOUD_SYNC_INTERVAL_SEC}s, só se consentido)...")
            self._cloud_sync_task = asyncio.create_task(self._cloud_sync_loop())

    async def _cloud_sync_loop(self):
        """Sobe o conteúdo do RAG local (knowledge_base.json inteiro,
        incluindo benchmarks) pro Firestore, de tempos em tempos. Só faz
        efeito se o usuário já tiver dado consentimento (ver
        /api/telemetry/consent no api_server.py)."""
        from phoenix_kernel.cloud_sync import get_or_create_machine_id
        while True:
            try:
                await asyncio.sleep(CLOUD_SYNC_INTERVAL_SEC)
                machine_id = get_or_create_machine_id()
                sent = await self.cloud_sync.sync(machine_id)
                if sent:
                    self.logs.add_event("INFO", "FirestoreSync", f"{sent} documento(s) sincronizado(s) com o Firestore.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"FirestoreSync: falha no loop de sync - {e}")
                self.logs.add_event("ERROR", "FirestoreSync", f"Falha ao sincronizar com o Firestore: {e}")

    async def shutdown(self):
        print("[Kernel] Desligando serviços...")
        self.logs.add_event("INFO", "Kernel", "Shutdown initiated.")
        if self._cloud_sync_task:
            self._cloud_sync_task.cancel()
        try: await self.runtime.shutdown()
        except: pass
