import asyncio
import importlib
import logging
from pathlib import Path
from core.events.bus import EventBus
from core.kernel.kernel import PlatformKernel
from core.domain.machine import MachineContext
from phoenix_kernel.state import StateEngine
from phoenix_kernel.cloud_sync import has_consent, FirestoreSync
from phoenix_kernel.services.ocr_engine import OCREngine
import setup_platform

logger = logging.getLogger(__name__)

CLOUD_SYNC_INTERVAL_SEC = 60

class PhoenixKernel:
    """
    PHOENIX KERNEL 3.0
    Orquestrador central e Composition Root.
    Responsável por instanciar e injetar todas as dependências seguindo a arquitetura oficial.
    """
    def __init__(self):
        self.event_bus = EventBus()
        self.platform_kernel = PlatformKernel()
        
        # --- 1. INFRAESTRUTURA E DESCOBERTA ---
        discovery_module = importlib.import_module("phoenix_kernel.discovery.engine")
        self.discovery = discovery_module.DiscoveryEngine()

        budget_module = importlib.import_module("phoenix_kernel.budget.engine")
        self.budget = budget_module.BudgetEngine()

        telemetry_module = importlib.import_module("phoenix_kernel.telemetry.engine")
        self.telemetry = telemetry_module.TelemetryEngine()

        # --- 2. SERVIÇOS E MODELOS ---
        services_module = importlib.import_module("phoenix_kernel.services.engine")
        self.services = services_module.ServicesEngine()

        # Legado/Compatibilidade (NÃO É O BACKEND PRINCIPAL)
        self.platform_process = importlib.import_module("phoenix_kernel.services.platform_process")
        self.lmstudio_service = importlib.import_module("phoenix_kernel.services.lmstudio_service")

        # PHX-FIX: Motor de OCR nativo para ler imagens coladas no chat ou anexadas
        self.ocr_engine = OCREngine()

        # PHX-FIX: ModelsEngine injetado ANTES do StateEngine e PlannerEngine 
        # para resolver o AttributeError e permitir o set_knowledge_engine.
        models_module = importlib.import_module("phoenix_kernel.models.engine")
        self.models = models_module.ModelsEngine()

        # --- 3. ESTADO E PLANEJAMENTO ---
        # Agora self.models existe e pode ser passado com segurança para o StateEngine
        self.state = StateEngine(self.budget, self.telemetry, self.services, self.models)
        
        planner_module = importlib.import_module("phoenix_kernel.planner.engine")
        self.planner = planner_module.PlannerEngine(self.event_bus, self.platform_kernel)
        self.models.set_knowledge_engine(self.planner.knowledge)

        # --- 4. RUNTIME ENGINE (ÚNICO RESPONSÁVEL POR EXECUÇÃO) ---
        runtime_module = importlib.import_module("phoenix_kernel.runtime.engine")
        self.runtime = runtime_module.RuntimeEngine(self.event_bus, self.platform_kernel)

        # --- 5. SEGURANÇA, LOGS E VALIDAÇÃO ---
        validation_module = importlib.import_module("phoenix_kernel.validation.engine")
        self.validation = validation_module.ValidationEngine()

        logs_module = importlib.import_module("phoenix_kernel.logs.engine")
        self.logs = logs_module.LogsEngine()

        security_module = importlib.import_module("phoenix_kernel.security.engine")
        self.security = security_module.SecurityEngine()

        # --- 6. RESIDENT MANAGER E REASONING ENGINE ---
        resident_module = importlib.import_module("phoenix_kernel.resident.resident_manager")
        self.resident = resident_module.ResidentManager(
            state_engine=self.state, 
            planner_engine=self.planner, 
            services_engine=self.services, 
            logs_engine=self.logs, 
            runtime_engine=self.runtime
            # PHX-FIX: Removida a injeção do model_manager pois o ResidentManager já o instancia internamente.
        )

        # --- 7. API ENGINE ---
        api_module = importlib.import_module("phoenix_kernel.api.engine")
        self.api = api_module.ApiEngine(
            self.state, self.models, self.planner, self.runtime, 
            self.services, self.logs, self.validation, self.security, self.resident,
            self.ocr_engine
        )
        
        self.machine_context = None
        self._cloud_sync_task = None
        
        # --- 8. CLOUD SYNC ---
        self.cloud_sync = None
        try:
            self.cloud_sync = FirestoreSync()
        except Exception:
            logger.warning("Biblioteca google-cloud-firestore não instalada ou credenciais ausentes. Sincronização na nuvem desativada.")

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

        # PHX-FIX (corrigido): antes disparava o download do .gguf em
        # background e IMEDIATAMENTE tentava subir o llama.cpp na sequência
        # - o servidor sempre falhava na primeira instalação, porque o
        # arquivo ainda não existia (Path.exists() só confirma que o
        # download terminou, não que ele foi disparado). Agora:
        # - se o modelo já está pronto e íntegro -> sobe o motor na hora.
        # - se não está -> sobe em background só DEPOIS que o download
        #   validar como completo, sem travar o boot da API nesse meio tempo.
        from core.domain.execution import ExecutionPlan as BootPlan
        boot_plan = BootPlan(runtime="llama.cpp", model="qwen3:8b", parameters={}, reasoning="Bootstrap")

        model_ready = await self._ensure_default_model()

        if model_ready:
            print("[Kernel] Subindo Servidor LLM Nativo (llama.cpp) na porta 8081 [CPU Policy]...")
            await self._start_llm_engine(boot_plan)
        else:
            print("[Kernel] Modelo padrão ainda baixando - Servidor LLM (llama.cpp) vai subir sozinho quando o download terminar.")
            self.logs.add_event("INFO", "Kernel", "Aguardando download do modelo padrão para subir o Servidor LLM.")
            asyncio.create_task(self._start_llm_engine_when_ready(boot_plan))

        print("[Kernel] Preparando Phoenix Aviary Platform (porta 3000)...")
        ok, msg = setup_platform.build_platform()
        self.logs.add_event("INFO" if ok else "ERROR", "PlatformProcess", msg)
        if ok:
            self.platform_process.start_supervised(self.logs)
        else:
            self.logs.add_event("WARNING", "PlatformProcess", "Platform não disponível na porta 3000 até o problema acima ser resolvido.")

        print("[Kernel] Verificando LM Studio (porta 1234) - Legado...")
        lm_ok, lm_msg = await self.lmstudio_service.try_start_server(self.logs)
        self.logs.add_event("INFO" if lm_ok else "WARNING", "LMStudioService", lm_msg)

        if self.cloud_sync is not None:
            print(f"[Kernel] Iniciando loop de sincronização com o Firestore (a cada {CLOUD_SYNC_INTERVAL_SEC}s, só se consentido)...")
            self._cloud_sync_task = asyncio.create_task(self._cloud_sync_loop())

    async def _start_llm_engine(self, boot_plan) -> bool:
        """Sobe o llama.cpp e loga o resultado. Isolado em método próprio
        porque agora é chamado de dois lugares: na hora (modelo já pronto)
        ou depois, quando o download em background termina."""
        llm_ok = await self.runtime.start("llama.cpp", boot_plan)
        if llm_ok:
            self.logs.add_event("INFO", "Kernel", "Servidor LLM ativo na porta 8081.")
            print("[Kernel] ✅ Servidor LLM ativo na porta 8081.")
        else:
            self.logs.add_event("ERROR", "Kernel", "Falha ao subir Servidor LLM na porta 8081.")
            print("[Kernel] ❌ Falha ao subir Servidor LLM (Verifique se o download do .gguf concluiu).")
        return llm_ok

    async def _start_llm_engine_when_ready(self, boot_plan, timeout_seconds: int = 1800, poll_interval: int = 5):
        """Espera o download do modelo padrão terminar (com timeout) e só
        então sobe o llama.cpp. Roda em background (asyncio.create_task),
        não bloqueia o boot da API."""
        from phoenix_kernel.paths import PhoenixPaths
        model_path = PhoenixPaths.get_category_path("Chat", "GGUF") / "qwen3-8b-q4_k_m.gguf"
        min_valid_size_bytes = 1_000_000_000  # 1GB - abaixo disso, arquivo truncado/corrompido

        waited = 0
        while waited < timeout_seconds:
            if model_path.exists() and model_path.stat().st_size >= min_valid_size_bytes:
                print("[Kernel] Download do modelo padrão concluído - subindo Servidor LLM agora.")
                await self._start_llm_engine(boot_plan)
                return
            await asyncio.sleep(poll_interval)
            waited += poll_interval

        logger.error(f"Kernel: modelo padrão não ficou pronto após {timeout_seconds}s de espera - desistindo de subir o llama.cpp automaticamente.")
        self.logs.add_event("ERROR", "Kernel", f"Timeout ({timeout_seconds}s) esperando download do modelo padrão - Servidor LLM não foi iniciado.")

    async def _ensure_default_model(self) -> bool:
        """Verifica se o modelo padrão para raciocínio nativo existe E é
        válido (checagem de tamanho mínimo, não só Path.exists() - um
        download interrompido/disco cheio deixa o arquivo presente só que
        truncado, e Path.exists() sozinho nunca detectava isso). Se não
        estiver pronto, dispara o download em background e retorna False.
        Retorna True só quando o modelo está pronto pra uso imediato."""
        from phoenix_kernel.paths import PhoenixPaths
        model_path = PhoenixPaths.get_category_path("Chat", "GGUF") / "qwen3-8b-q4_k_m.gguf"
        min_valid_size_bytes = 1_000_000_000  # 1GB - Q4_K_M do Qwen3-8B fica na faixa de 4.5-5GB

        if model_path.exists():
            size = model_path.stat().st_size
            if size >= min_valid_size_bytes:
                print(f"[Kernel] Modelo padrão (qwen3:8b) encontrado no disco ({size / 1e9:.2f} GB).")
                return True
            else:
                print(f"[Kernel] Modelo padrão (qwen3:8b) encontrado mas incompleto/corrompido ({size} bytes) - baixando de novo.")
                self.logs.add_event("WARNING", "Kernel", f"Arquivo .gguf incompleto detectado ({size} bytes) - reiniciando download.")
                try:
                    model_path.unlink()
                except Exception as e:
                    logger.error(f"Kernel: falha ao remover arquivo .gguf corrompido: {e}")

        print("[Kernel] Modelo padrão (qwen3:8b) ausente no disco. Iniciando download em background...")
        self.logs.add_event("WARNING", "Kernel", "Baixando modelo padrão para raciocínio nativo...")

        try:
            # Instancia o ModelManager localmente para garantir o download sem acoplamento
            _models_module = importlib.import_module("phoenix_kernel.models.model_manager")
            ModelManager = _models_module.ModelManager
            mm = ModelManager()

            # Dispara o download em segundo plano para não travar o boot da API
            asyncio.create_task(mm.download_model("qwen3:8b"))
        except Exception as e:
            logger.error(f"Kernel: Falha ao iniciar download do modelo padrão: {e}")

        return False

    async def _cloud_sync_loop(self):
        await self.cloud_sync.sync_knowledge_base()
        while True:
            try:
                await asyncio.sleep(CLOUD_SYNC_INTERVAL_SEC)
                state_data = await self.state.get_state()
                await self.cloud_sync.sync_machine_state(state_data)
                if has_consent():
                    self.logs.add_event("INFO", "FirestoreSync", "Telemetria sincronizada com a nuvem.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"FirestoreSync: falha no loop de sync - {e}")
                self.logs.add_event("ERROR", "FirestoreSync", f"Falha ao sincronizar com o Firestore: {e}")

    async def shutdown(self):
        print("[Kernel] Desligando serviços...")
        self.logs.add_event("INFO", "Kernel", "Shutdown initiated.")

        await self.platform_process.stop()

        if self._cloud_sync_task:
            self._cloud_sync_task.cancel()
        
        if self.cloud_sync is not None:
            self.cloud_sync.shutdown()
            
        try: 
            await self.runtime.shutdown()
        except: 
            pass