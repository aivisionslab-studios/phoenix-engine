import asyncio
import logging
import importlib
import re
import time
from datetime import datetime, timezone

from .interfaces import IResidentManager
from phoenix_kernel.intelligence.reasoning_engine import ReasoningEngine
from phoenix_kernel.core.enums import MissionStatus, MissionAction
from phoenix_kernel.core.kernel import MissionKernel
from phoenix_kernel.core.exceptions import NoActiveMissionError
from core.domain.execution import ExecutionPlan, ExecutionStatus

logger = logging.getLogger(__name__)

_hardware_core = importlib.import_module("phoenix_kernel.telemetry.core")
_models_module = importlib.import_module("phoenix_kernel.models.model_manager")
_paths_module = importlib.import_module("phoenix_kernel.paths")
# PHX-NEW (Fase 2 - Abstração de Capacidades): Model Registry. Antes,
# "qwen3:8b"/"minicpmv"/"flux"/"pt_br-faber-medium" apareciam como string
# literal espalhados pelo código - trocar o modelo padrão de uma
# capacidade exigia caçar e editar em vários lugares. Agora
# catalog/models.json declara isso e o ResidentManager só pede uma ROLE
# (ex: "vision", "image_generation", "chat") pro registry.resolve() -
# mesmo princípio de abstração que phoenix_kernel/documents/engine.py já
# aplica pra formato de arquivo.
_registry_module = importlib.import_module("phoenix_kernel.models.registry")
ModelManager = _models_module.ModelManager
PhoenixPaths = _paths_module.PhoenixPaths
ModelRegistry = _registry_module.ModelRegistry

HOT_TEMP_C = 80.0
HIGH_LOAD_PCT = 90.0

# PHX-FIX: padrões usados para classificar a arquitetura de um .gguf de
# imagem só pelo nome do arquivo. Isso é o mesmo critério que o
# SdCppDriver já usa pra decidir -m vs --diffusion-model - centralizado
# aqui pra não divergir entre os dois lugares.
_IMAGE_ARCH_PATTERNS = {
    "flux": ("flux",),
    "sd15": ("dreamshaper", "sd15", "sd-1", "sd1.5", "sd_1_5"),
    "sdxl": ("sdxl", "xl-base", "xl_base"),
}


class ResidentManager(IResidentManager):
    def __init__(self, state_engine, planner_engine, services_engine, logs_engine, runtime_engine=None, model_manager=None, model_registry=None):
        self.state = state_engine
        self.planner = planner_engine
        self.services = services_engine
        self.logs = logs_engine
        self.runtime = runtime_engine

        # PHX-NEW (Fase 2): Model Registry - injetável (mesmo padrão de
        # model_manager abaixo) pra facilitar teste com um catálogo fake,
        # ou cria o real lendo catalog/models.json se ninguém injetar.
        self.registry = model_registry if model_registry else ModelRegistry()

        # PHX-FIX: Injeta runtime_engine E logs_engine no ReasoningEngine - o
        # runtime pra usar o driver nativo (Vulkan), os logs pra você ver o
        # "pensamento" ao vivo no painel em vez do terminal ficar mudo.
        # PHX-NEW (Fase 2): também injeta o registry - o ReasoningEngine não
        # decide mais sozinho qual modelo de texto usar (era DEFAULT_MODEL =
        # "qwen3:8b" hardcoded).
        self.reasoning = ReasoningEngine(state_engine, runtime_engine=self.runtime, logs_engine=self.logs, model_registry=self.registry)

        # PHX-FIX: Usa o ModelManager injetado pelo Kernel ou cria um fallback
        self.model_manager = model_manager if model_manager else ModelManager()

        # PHX-FIX (auditoria segunda rodada): MissionKernel existia como
        # classe isolada (criada pra destravar os testes), mas o ResidentManager
        # usava self._active_mission ad hoc, ignorando completamente o portao
        # de aprovacao. Agora o fluxo real passa pelo MissionKernel — o mesmo
        # objeto que os testes exercitam, tornando-os cobertura do caminho real.
        self._mission_kernel = MissionKernel()
        self._active_mission = None  # mantido so pra compatibilidade de leitura em get_status()

        # PHX-NEW: fila de mensagens que o Resident decide mandar direto
        # pro Chat WebUI (porta 3000), sem passar por missão de
        # provisionamento - populada em process_intent() quando
        # reasoning.plan_mission() devolve None mas reasoning.last_response
        # veio preenchido (campo "response" do JSON, ver reasoning_engine.py).
        # api_server.py serve isso em GET /api/chat/pending e limpa ao servir.
        self.pending_chat_messages: list[dict] = []

    async def analyze_machine(self) -> str:
        """Coleta specs do State, faz a leitura completa de sensores, pede ao 
        Planner (RAG) uma sugestão de plano."""
        logger.info("ResidentManager: Iniciando análise de máquina...")
        state_data = await self.state.get_state()

        if "error" in state_data:
            return "Sistema ainda inicializando. Aguarde o Discovery concluir."

        hw = state_data.get("hardware", {})
        budget = state_data.get("budget", {})

        loop = asyncio.get_running_loop()
        try:
            devices = await loop.run_in_executor(None, _hardware_core.get_all_hardware_sensors)
        except Exception as e:
            logger.warning(f"ResidentManager: falha ao ler sensores completos - {e}")
            devices = []

        alerts = self._check_device_alerts(devices)

        query = f"Melhor configuração LLM para {hw.get('gpu', 'CPU')} com {hw.get('vram_mb', 0)}MB VRAM"
        # PHX-FIX (auditoria 2026-08-04): query_knowledge() é síncrono e
        # retorna list[str] — o "await" aqui levantava TypeError sem
        # nenhum try/except ao redor, derrubando analyze_hardware() toda
        # vez que era chamado. O código abaixo também presumia um dict
        # (.get('name'/'notes')), que nunca correspondeu ao formato real.
        try:
            rag_hits = self.planner.knowledge.query_knowledge(query)
        except Exception as e:
            logger.warning(f"ResidentManager: falha ao consultar RAG ({e}).")
            rag_hits = []

        report = "🔍 PHOENIX RESIDENT MANAGER - ANÁLISE DE HARDWARE 🔍\n\n"
        report += f"CPU: {hw.get('cpu', 'N/A')}\n"
        report += f"RAM: {hw.get('ram_mb', 0)} MB\n"
        report += f"GPU: {hw.get('gpu', 'N/A')} ({hw.get('vram_mb', 0)} MB VRAM)\n"
        report += f"Backends: {', '.join(hw.get('backends', []))}\n"
        report += f"Classe da Máquina: {budget.get('class', 'Unknown')} (Score: {budget.get('score', 0)}%)\n\n"

        report += f"📡 SCANNER COMPLETO: {len(devices)} dispositivo(s) ativo(s) lido(s)\n"
        if alerts:
            report += "⚠️ ALERTAS DE SENSOR:\n"
            for a in alerts:
                report += f"- {a['device']} / {a['sensor_name']}: {a['value']:.0f}{a['unit']} (acima de {a['threshold']:.0f}{a['unit']})\n"
        else:
            report += "Nenhum sensor fora da faixa normal no momento.\n"
        report += "\n"

        report += "💡 SUGESTÃO DE PLANO (Baseado no histórico RAG):\n"
        if rag_hits:
            report += "Baseado em testes anteriores, recomenda-se:\n"
            for hit in rag_hits:
                report += f"- {hit}\n"
        else:
            report += "Nenhuma recomendação histórica exata encontrada. Plano padrão: Instalar Ollama e OpenWebUI.\n"

        report += "\n⚠️ Nenhuma ação de execução foi tomada. A Phoenix apenas pensou."
        return report

    @staticmethod
    def _check_device_alerts(devices: list) -> list:
        alerts = []
        for dev in devices:
            for s in dev.get("sensors", []):
                if s["type"] == "Temperature" and s["value"] >= HOT_TEMP_C:
                    alerts.append({
                        "device": dev["name"], "sensor_name": s["name"], "sensor_type": s["type"],
                        "value": s["value"], "unit": "°C", "threshold": HOT_TEMP_C,
                    })
                elif s["type"] == "Load" and s["value"] >= HIGH_LOAD_PCT:
                    alerts.append({
                        "device": dev["name"], "sensor_name": s["name"], "sensor_type": s["type"],
                        "value": s["value"], "unit": "%", "threshold": HIGH_LOAD_PCT,
                    })
        return alerts

    async def _thermal_guard(self, context: str) -> None:
        """PHX-FIX: checagem térmica não-bloqueante antes de passos pesados de
        GPU (ex: GENERATE_IMAGE). Não aborta a missão - só avisa no log, já
        que decidir "abortar por causa de temperatura" é uma decisão do
        usuário, não do Resident Manager."""
        try:
            loop = asyncio.get_running_loop()
            devices = await loop.run_in_executor(None, _hardware_core.get_all_hardware_sensors)
            alerts = self._check_device_alerts(devices)
            gpu_alerts = [a for a in alerts if "gpu" in a["device"].lower() or "radeon" in a["device"].lower()]
            if gpu_alerts:
                for a in gpu_alerts:
                    self.logs.add_event(
                        "WARNING", "MissionExecutor",
                        f"⚠️ {context}: {a['device']} / {a['sensor_name']} em {a['value']:.0f}{a['unit']} "
                        f"(limite {a['threshold']:.0f}{a['unit']}) - prosseguindo mesmo assim."
                    )
        except Exception as e:
            logger.warning(f"ResidentManager: guarda térmica falhou ao ler sensores - {e}")

    # ============================================================
    # PHX-FIX: DESCOBERTA DE MODELO NO DISCO (não confia no LLM)
    # ============================================================
    #
    # Antes disso, GENERATE_IMAGE simplesmente pegava `step.target` — o
    # nome do modelo que o LLM colocou no plano — e mandava direto pro
    # SdCppDriver. Problema: o LLM "lembra" de modelos por texto, não vê
    # o disco. Ele podia planejar "sdxl" numa sessão onde o único modelo
    # de imagem baixado de verdade era FLUX (ou o contrário), e a missão
    # falhava tentando rodar um arquivo que nunca existiu.
    #
    # A regra nova é simples: ENXERGAR primeiro, SETAR depois.
    # 1. Escaneia a pasta de modelos de Imagem no disco de verdade.
    # 2. Se o que o LLM pediu bate com algo já baixado -> usa esse.
    # 3. Se não bate mas existe ALGO baixado -> usa o mais recente
    #    (assume que foi o último que o usuário baixou de propósito).
    # 4. Só se não tiver NADA no disco é que aciona o download.

    def _discover_installed_image_models(self) -> list[dict]:
        """Enxerga o que já foi baixado de verdade, escaneando o disco."""
        try:
            image_dir = PhoenixPaths.get_category_path("Image")
        except Exception as e:
            logger.warning(f"ResidentManager: falha ao resolver pasta 'Image' - {e}")
            return []

        if not image_dir.exists():
            return []

        found = []
        for gguf_file in image_dir.rglob("*.gguf"):
            name_lower = gguf_file.stem.lower()
            arch = "unknown"
            for arch_name, keywords in _IMAGE_ARCH_PATTERNS.items():
                if any(kw in name_lower for kw in keywords):
                    arch = arch_name
                    break
            try:
                mtime = gguf_file.stat().st_mtime
            except OSError:
                mtime = 0.0
            found.append({"path": gguf_file, "name": gguf_file.stem, "architecture": arch, "mtime": mtime})

        # Mais recente primeiro - se tem mais de um modelo de imagem
        # instalado, o mais recentemente baixado é o candidato mais provável
        # a ser "o que o usuário quer usar agora".
        found.sort(key=lambda f: f["mtime"], reverse=True)
        return found

    def _resolve_image_model_target(self, step_target: str) -> tuple[str | None, str]:
        """Decide qual modelo de imagem vai ser usado de verdade.

        Retorna (nome_do_modelo_ou_None, mensagem_explicando_a_decisão).
        `None` significa "nada disso está instalado, alguém precisa baixar".
        """
        installed = self._discover_installed_image_models()
        clean_target = (step_target or "").split(":")[0].replace("/", "-").lower()

        # 1. O que o plano pediu já está instalado? Usa sem drama.
        for model in installed:
            if clean_target and clean_target in model["name"].lower():
                return model["name"], f"'{model['name']}' já está instalado e bate com o plano."

        # 2. Não bate, mas existe ALGUMA coisa de imagem já baixada no disco.
        # Em vez de tentar rodar um arquivo fantasma que o LLM inventou,
        # usa o que realmente existe.
        if installed:
            chosen = installed[0]
            return chosen["name"], (
                f"plano pedia '{step_target}', mas isso não está no disco. "
                f"Usando '{chosen['name']}' (modelo de imagem já instalado, mais recente) em vez disso."
            )

        # 3. Nada instalado de verdade. Quem chamou decide se baixa.
        return None, f"nenhum modelo de imagem encontrado no disco (plano pedia '{step_target}')."

    # ============================================================
    # DESCOBERTA DE VOZES INSTALADAS (Piper) — mesmo padrão do bloco
    # de imagem acima: ENXERGAR o disco primeiro, nunca assumir.
    # ============================================================

    def _discover_installed_voices(self) -> list[dict]:
        """Enxerga quais vozes Piper (.onnx + .onnx.json) já foram
        baixadas de verdade, escaneando o disco."""
        try:
            voice_dir = PhoenixPaths.get_category_path("Voice", "Piper")
        except Exception as e:
            logger.warning(f"ResidentManager: falha ao resolver pasta 'Voice/Piper' - {e}")
            return []

        if not voice_dir.exists():
            return []

        found = []
        for onnx_file in voice_dir.rglob("*.onnx"):
            config_path = onnx_file.with_suffix(onnx_file.suffix + ".json")
            if not config_path.exists():
                continue  # par incompleto - piper exige os dois arquivos
            try:
                mtime = onnx_file.stat().st_mtime
            except OSError:
                mtime = 0.0
            found.append({"path": onnx_file, "name": onnx_file.stem, "mtime": mtime})

        found.sort(key=lambda f: f["mtime"], reverse=True)
        return found

    def _resolve_voice_target(self, voice_hint: str) -> tuple[str | None, str]:
        """Decide qual voz Piper vai ser usada de verdade — mesma lógica de
        3 passos de _resolve_image_model_target (bate com o pedido -> usa;
        não bate mas tem algo instalado -> usa o mais recente; nada
        instalado -> None pra quem chamou decidir)."""
        installed = self._discover_installed_voices()
        clean_hint = (voice_hint or "").split(":")[0].lower()

        for voice in installed:
            if clean_hint and clean_hint in voice["name"].lower():
                return voice["name"], f"'{voice['name']}' já está instalada e bate com o pedido."

        if installed:
            chosen = installed[0]
            return chosen["name"], (
                f"pedido era '{voice_hint}', mas essa voz não está no disco. "
                f"Usando '{chosen['name']}' (voz Piper mais recente instalada) em vez disso."
            )

        return None, f"nenhuma voz Piper encontrada no disco (pedido era '{voice_hint}')."

    # ============================================================
    # INTEGRAÇÃO REASONING ENGINE (O CÉREBRO)
    # ============================================================

    async def process_intent(self, intent: str) -> dict:
        """Recebe a intenção do usuário, pede ao LLM para pensar e devolve o plano."""
        mission = await self.reasoning.plan_mission(intent)

        if not mission:
            # PHX-NEW: sem missão, mas o LLM gerou uma resposta direta
            # (campo "response" do JSON - ver reasoning_engine.py). Enfileira
            # pro Chat WebUI (porta 3000) consumir via /api/chat/pending, em
            # vez de tratar como erro.
            direct_response = getattr(self.reasoning, "last_response", None)
            if direct_response:
                self.pending_chat_messages.append({"content": direct_response, "model": "phoenix-resident"})
                self.logs.add_event("INFO", "ResidentManager", "Resposta direta enfileirada para o Chat WebUI.")
                return {"output": direct_response}

            # PHX-FIX: Expõe o motivo real (guardado pelo ReasoningEngine em
            # last_error) em vez da mensagem genérica que escondia se o
            # llama-cli realmente falhou, deu timeout, ou devolveu algo que
            # não era JSON.
            detail = getattr(self.reasoning, "last_error", None) or "motivo desconhecido"
            return {"output": f"[ERRO] O cérebro (LLM) não respondeu: {detail}"}

        self._mission_kernel.register(mission)
        self._active_mission = mission  # espelho para get_status()

        return {
            "output": f"Plano criado: {mission.metadata.get('llm_reasoning', '')}\nAguardando aprovação.",
            "mission": mission.to_dict()
        }

    async def approve_and_execute(self) -> dict:
        """Aprova a missão pendente e aciona a execução em Background."""
        try:
            mission = self._mission_kernel.approve_active_mission()
        except NoActiveMissionError:
            return {"output": "Nenhuma missão pendente para aprovação."}

        mission.status = MissionStatus.RUNNING

        # Dispara a execução em segundo plano para não travar o terminal do painel
        asyncio.create_task(self._execute_mission_background(mission))

        self._active_mission = None
        self._mission_kernel._active = None  # limpa o portao apos despachar

        return {
            "output": f"✅ Missão aprovada! O Kernel iniciou a execução de {len(mission.steps)} passo(s) em segundo plano.\nDigite 'logs' para acompanhar o progresso."
        }

    async def _execute_mission_background(self, mission):
        """Executa os passos da missão acionando o ServicesEngine real."""
        mission_start = time.monotonic()
        self.logs.add_event("INFO", "MissionKernel", f"Iniciando execução da missão: {mission.intent}")

        for step in mission.steps:
            step_start = time.monotonic()
            step_log_msg = f"[Passo {step.step}] {step.description} (Ação: {step.action.value}, Alvo: {step.target})"
            self.logs.add_event("INFO", "MissionExecutor", step_log_msg)
            logger.info(f"[MissionExecutor] {step_log_msg}")

            try:
                if step.action == MissionAction.VALIDATE_ENVIRONMENT:
                    env_status = await self.services.get_environment_status()
                    is_ok = env_status.get(step.target.lower(), False)
                    if not is_ok:
                        self.logs.add_event("WARNING", "MissionExecutor", f"Alvo '{step.target}' não está pronto. Tentando instalar...")
                        await self.services.install_service(step.target.lower())

                elif step.action == MissionAction.INSTALL_PACKAGE:
                    result = await self.services.install_service(step.target.lower())
                    self.logs.add_event("INFO", "MissionExecutor", f"Resultado: {result}")

                elif step.action == MissionAction.DOWNLOAD_MODEL:
                    # PHX-FIX: só baixa se REALMENTE não tiver nada
                    # equivalente já instalado. Antes ele baixava sem
                    # checar disco, então rodar a mesma missão duas vezes
                    # baixava o mesmo modelo duas vezes.
                    if _is_image_model_target(step.target):
                        resolved, note = self._resolve_image_model_target(step.target)
                        self.logs.add_event("INFO", "MissionExecutor", f"Verificação no disco: {note}")
                        if resolved is not None:
                            self.logs.add_event("INFO", "MissionExecutor", f"'{resolved}' já está instalado. Pulando download.")
                            step_elapsed = time.monotonic() - step_start
                            self.logs.add_event("INFO", "MissionExecutor", f"[Passo {step.step}] concluído em {step_elapsed:.1f}s.")
                            continue

                    self.logs.add_event("INFO", "MissionExecutor", f"ModelManager: Baixando modelo {step.target}...")
                    result = await self.model_manager.download_model(step.target)
                    if result is None:
                        self.logs.add_event("INFO", "MissionExecutor", f"Resultado: modelo '{step.target}' não gerou arquivo local (ollama-only) ou o download falhou.")
                        self.logs.add_event("ERROR", "MissionExecutor", f"Falha no download de '{step.target}'. Missão interrompida neste passo.")
                        break
                    self.logs.add_event("INFO", "MissionExecutor", f"Resultado: {result}")

                elif step.action == MissionAction.SWITCH_RUNTIME:
                    if self.runtime is None:
                        self.logs.add_event("ERROR", "MissionExecutor", "RuntimeEngine não disponível (não injetado no ResidentManager). Troca de runtime abortada.")
                        break

                    target_runtime = step.target.lower()  # ex: "llama.cpp" ou "ollama"
                    from_runtime = step.metadata.get("from_runtime") if hasattr(step, "metadata") and step.metadata else None

                    if from_runtime:
                        self.logs.add_event("INFO", "MissionExecutor", f"RuntimeEngine: Parando '{from_runtime}'...")
                        await self.runtime.stop(from_runtime)

                    plan_params = step.metadata.get("plan") if hasattr(step, "metadata") and step.metadata else None
                    self.logs.add_event("INFO", "MissionExecutor", f"RuntimeEngine: Iniciando '{target_runtime}'...")
                    success = await self.runtime.start(target_runtime, plan_params)

                    if not success:
                        self.logs.add_event("ERROR", "MissionExecutor", f"Falha ao iniciar '{target_runtime}'. Missão interrompida neste passo.")
                        break
                    self.logs.add_event("INFO", "MissionExecutor", f"RuntimeEngine: '{target_runtime}' ativo com sucesso.")

                elif step.action == MissionAction.LOAD_MODEL:
                    # PHX-NEW: troca o modelo de TEXTO carregado no mesmo
                    # runtime (llama.cpp), diferente de SWITCH_RUNTIME (que
                    # troca de MOTOR - llama.cpp vs sdxl vs piper). Depende
                    # do fix em LlamaCppDriver.start() que agora compara o
                    # arquivo do modelo pedido com o que já está carregado
                    # antes de decidir se recarrega - sem isso, esta ação
                    # seria um no-op se já houvesse qualquer processo de pé.
                    if self.runtime is None:
                        self.logs.add_event("ERROR", "MissionExecutor", "RuntimeEngine não disponível (não injetado no ResidentManager). Troca de modelo abortada.")
                        break

                    target_model = step.target
                    target_runtime = (step.parameters or {}).get("runtime", "llama.cpp")

                    plan = ExecutionPlan(
                        runtime=target_runtime, model=target_model, parameters={},
                        reasoning=step.description or f"Carregar modelo '{target_model}'",
                    )
                    self.logs.add_event("INFO", "MissionExecutor", f"RuntimeEngine: carregando modelo '{target_model}' em '{target_runtime}'...")
                    success = await self.runtime.start(target_runtime, plan)

                    if not success:
                        self.logs.add_event("ERROR", "MissionExecutor", f"Falha ao carregar modelo '{target_model}'. Missão interrompida neste passo.")
                        break
                    self.logs.add_event("INFO", "MissionExecutor", f"Modelo '{target_model}' carregado com sucesso em '{target_runtime}'.")

                elif step.action == MissionAction.UNLOAD_MODEL:
                    # PHX-NEW: libera o modelo de texto atualmente carregado
                    # (RAM/VRAM) sem carregar outro no lugar - útil quando a
                    # missão termina uma tarefa pesada e não precisa manter
                    # nada residente até a próxima intenção do usuário.
                    if self.runtime is None:
                        self.logs.add_event("ERROR", "MissionExecutor", "RuntimeEngine não disponível (não injetado no ResidentManager). Descarregar modelo abortado.")
                        break

                    target_runtime = step.target.lower() if step.target else "llama.cpp"
                    self.logs.add_event("INFO", "MissionExecutor", f"RuntimeEngine: descarregando '{target_runtime}'...")
                    await self.runtime.stop(target_runtime)
                    self.logs.add_event("INFO", "MissionExecutor", f"'{target_runtime}' descarregado - memória liberada.")

                elif step.action == MissionAction.GENERATE_IMAGE:
                    if self.runtime is None:
                        self.logs.add_event("ERROR", "MissionExecutor", "RuntimeEngine não disponível (não injetado no ResidentManager). Geração de imagem abortada.")
                        break

                    # PHX-FIX: checa temperatura/carga da GPU antes de disparar
                    # a etapa mais pesada da missão (não bloqueia, só avisa).
                    await self._thermal_guard("Antes de gerar imagem")

                    # PHX-FIX (o núcleo desta mudança): não confia mais
                    # cegamente em `step.target`. Enxerga o disco primeiro.
                    # Isso resolve o caso "baixou FLUX, plano ainda quer
                    # rodar sdxl/SD1.5" (ou o oposto) - o Executor agora usa
                    # o que está de fato instalado, e só chama o
                    # ModelManager se realmente não achar nada.
                    resolved_model, resolution_note = self._resolve_image_model_target(step.target)
                    self.logs.add_event("INFO", "MissionExecutor", f"Resolução de modelo de imagem: {resolution_note}")

                    if resolved_model is None:
                        self.logs.add_event(
                            "WARNING", "MissionExecutor",
                            f"Nenhum modelo de imagem instalado. Baixando '{step.target}' antes de gerar..."
                        )
                        download_result = await self.model_manager.download_model(step.target)
                        if download_result is None:
                            self.logs.add_event("ERROR", "MissionExecutor", f"Falha ao baixar '{step.target}'. Geração de imagem abortada.")
                            break
                        resolved_model = step.target

                    prompt = (step.parameters or {}).get("prompt", "A beautiful cyberpunk city, highly detailed")
                    plan = ExecutionPlan(
                        runtime="sdxl",  # Chama o SdCppDriver (Stable Diffusion), NÃO o llama.cpp
                        model=resolved_model,
                        parameters={"prompt": prompt},
                        reasoning=step.description,
                    )
                    # Log explícito para provar que não está usando o LLM (llama.cpp) para gerar imagem
                    self.logs.add_event("INFO", "MissionExecutor", f"RuntimeEngine (Stable Diffusion): gerando imagem com '{resolved_model}' na GPU (prompt: \"{prompt}\")...")
                    result = await self.runtime.execute(plan)

                    if result.status != ExecutionStatus.SUCCESS:
                        self.logs.add_event("ERROR", "MissionExecutor", f"Falha ao gerar imagem: {result.errors}. Missão interrompida neste passo.")
                        break
                    self.logs.add_event("INFO", "MissionExecutor", f"Resultado: {result.output}")

                else:
                    self.logs.add_event("WARNING", "MissionExecutor", f"Ação {step.action.value} ainda não implementada no Executor.")

            except Exception as e:
                err_msg = f"Falha crítica no passo {step.step}: {str(e)}"
                self.logs.add_event("ERROR", "MissionExecutor", err_msg)
                logger.error(f"[MissionExecutor] {err_msg}")
                break

            # PHX-FIX: telemetria de duração por passo - antes não dava pra
            # saber quanto cada etapa custou, só que "rodou".
            step_elapsed = time.monotonic() - step_start
            self.logs.add_event("INFO", "MissionExecutor", f"[Passo {step.step}] concluído em {step_elapsed:.1f}s.")

        mission_elapsed = time.monotonic() - mission_start
        self.logs.add_event("INFO", "MissionKernel", f"Execução da missão concluída em {mission_elapsed:.1f}s.")

    # ============================================================
    # PONTE DIRETA (Opção B2): geração de imagem síncrona, sem passar
    # pelo Mission Kernel / aprovação. Chamada pelo endpoint HTTP
    # POST /api/generate-image, usado pelo Chat WebUI do Phoenix Aviary.
    #
    # Reaproveita a MESMA lógica do passo GENERATE_IMAGE de dentro de uma
    # missão normal (_resolve_image_model_target, _thermal_guard,
    # runtime.execute) — não duplica regra nenhuma, só pula o
    # think/aprovar/rejeitar pra ficar síncrono o suficiente pra um chat.
    # ============================================================
    async def generate_image_direct(self, prompt: str, model_hint: str = "") -> dict:
        """Gera uma imagem AGORA, sem aprovação de missão. Retorna um dict
        com sucesso/erro e o caminho do arquivo gerado (se houver)."""
        if self.runtime is None:
            return {"ok": False, "error": "RuntimeEngine não disponível (não injetado no ResidentManager)."}

        prompt = (prompt or "").strip()
        if not prompt:
            return {"ok": False, "error": "Prompt vazio."}

        await self._thermal_guard("Antes de gerar imagem (ponte direta)")

        # PHX-NEW (Fase 2): "flux" hardcoded virou registry.resolve() -
        # ainda cai no mesmo default (Flux é default_for_roles de
        # image_generation no catalog/models.json), mas agora é
        # declarativo, não um literal solto no meio da lógica.
        default_image_model = self.registry.resolve("image_generation", hint=model_hint)
        target_for_disk_scan = default_image_model.id if default_image_model else (model_hint or "flux")
        resolved_model, resolution_note = self._resolve_image_model_target(target_for_disk_scan)
        self.logs.add_event("INFO", "DirectImageBridge", f"Resolução de modelo de imagem: {resolution_note}")

        if resolved_model is None:
            self.logs.add_event(
                "WARNING", "DirectImageBridge",
                f"Nenhum modelo de imagem instalado no disco. Baixe um modelo antes de gerar pela ponte direta "
                f"(essa ponte não baixa modelo sozinha — só a missão completa com aprovação faz isso)."
            )
            return {
                "ok": False,
                "error": "Nenhum modelo de imagem instalado no disco ainda. Rode uma missão de 'Criar Imagens' "
                         "e aprove o download primeiro — a ponte direta do chat só gera com o que já existe local.",
            }

        plan = ExecutionPlan(
            runtime="sdxl",  # Mesmo alias usado pelo Mission Executor -> roteia pro SdCppDriver
            model=resolved_model,
            parameters={"prompt": prompt},
            reasoning=f"Ponte direta (chat Aviary): {prompt}",
        )

        self.logs.add_event(
            "INFO", "DirectImageBridge",
            f"Gerando imagem com '{resolved_model}' na GPU (prompt: \"{prompt}\")..."
        )
        result = await self.runtime.execute(plan)

        if result.status != ExecutionStatus.SUCCESS:
            self.logs.add_event("ERROR", "DirectImageBridge", f"Falha ao gerar imagem: {result.errors}")
            return {"ok": False, "error": "; ".join(result.errors) if result.errors else "Falha desconhecida na geração."}

        self.logs.add_event("INFO", "DirectImageBridge", f"Resultado: {result.output}")
        # result.output vem no formato "Imagem salva em: <path>" (ver sd_cpp.py) —
        # extrai só o caminho pra devolver pro endpoint HTTP servir o arquivo.
        file_path = result.output.replace("Imagem salva em:", "").strip()
        return {"ok": True, "path": file_path, "model": resolved_model}

    # ============================================================
    # PONTE DIRETA: síntese de voz síncrona (Piper), sem passar pelo
    # Mission Kernel / aprovação. Chamada pelo endpoint HTTP
    # POST /api/generate-speech, usado pelo Chat WebUI do Phoenix Aviary
    # em vez da API paga da OpenAI. Mesmo padrão de generate_image_direct
    # acima — reaproveita _resolve_voice_target/_thermal_guard/runtime.execute.
    # ============================================================
    async def generate_speech_direct(self, text: str, voice_hint: str = "") -> dict:
        """Sintetiza fala AGORA, sem aprovação de missão. Retorna um dict
        com sucesso/erro e o caminho do .wav gerado (se houver)."""
        if self.runtime is None:
            return {"ok": False, "error": "RuntimeEngine não disponível (não injetado no ResidentManager)."}

        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "Texto vazio."}

        await self._thermal_guard("Antes de sintetizar voz (ponte direta)")

        # PHX-NEW (Fase 2): "pt_br-faber-medium" hardcoded virou
        # registry.resolve() - mesmo default declarado no catalog/models.json.
        default_voice = self.registry.resolve("speech_synthesis", hint=voice_hint)
        target_for_disk_scan = default_voice.id if default_voice else (voice_hint or "pt_br-faber-medium")
        resolved_voice, resolution_note = self._resolve_voice_target(target_for_disk_scan)
        self.logs.add_event("INFO", "DirectSpeechBridge", f"Resolução de voz: {resolution_note}")

        if resolved_voice is None:
            self.logs.add_event(
                "WARNING", "DirectSpeechBridge",
                "Nenhuma voz Piper instalada no disco. Baixe uma voz (par .onnx + .onnx.json) em "
                "Workstations/Models/Voice/Piper antes de usar a ponte direta.",
            )
            return {
                "ok": False,
                "error": "Nenhuma voz Piper instalada no disco ainda. Baixe uma voz "
                         "(ex: pt_BR-faber-medium) em Workstations/Models/Voice/Piper primeiro — "
                         "a ponte direta do chat não baixa voz sozinha.",
            }

        plan = ExecutionPlan(
            runtime="piper",  # Mesmo alias registrado em runtime/engine.py -> roteia pro PiperDriver
            model=resolved_voice,
            parameters={"text": text},
            reasoning=f"Ponte direta (chat Aviary): síntese de voz ({len(text)} chars)",
        )

        self.logs.add_event(
            "INFO", "DirectSpeechBridge",
            f"Sintetizando fala com '{resolved_voice}' ({len(text)} caracteres de texto)...",
        )
        result = await self.runtime.execute(plan)

        if result.status != ExecutionStatus.SUCCESS:
            self.logs.add_event("ERROR", "DirectSpeechBridge", f"Falha ao sintetizar voz: {result.errors}")
            return {"ok": False, "error": "; ".join(result.errors) if result.errors else "Falha desconhecida na síntese."}

        self.logs.add_event("INFO", "DirectSpeechBridge", f"Resultado: {result.output}")
        # result.output vem no formato "Audio salvo em: <path>" (ver piper.py) —
        # extrai só o caminho pra devolver pro endpoint HTTP servir o arquivo.
        file_path = result.output.replace("Audio salvo em:", "").strip()
        return {"ok": True, "path": file_path, "voice": resolved_voice}

    # ============================================================
    # PONTE DIRETA: troca de modelo de texto síncrona, sem passar pelo
    # Mission Kernel / aprovação. Mesmo padrão de generate_image_direct/
    # generate_speech_direct acima - útil pro Resident (ou uma missão)
    # trocar de modelo no meio de uma tarefa sem precisar montar uma
    # missão completa só pra isso (ex: detectou tarefa de código, quer
    # subir o Qwen2.5-Coder na hora em vez do modelo de chat padrão).
    # ============================================================
    async def load_model_direct(self, model_name: str, runtime: str = "llama.cpp") -> dict:
        """Carrega `model_name` no `runtime` indicado AGORA. Se já for o
        modelo certo, LlamaCppDriver.start() detecta isso e não recarrega
        à toa (ver PHX-FIX no llama_cpp.py). Retorna dict com sucesso/erro."""
        if self.runtime is None:
            return {"ok": False, "error": "RuntimeEngine não disponível (não injetado no ResidentManager)."}

        model_name = (model_name or "").strip()
        if not model_name:
            return {"ok": False, "error": "Nome do modelo vazio."}

        plan = ExecutionPlan(
            runtime=runtime, model=model_name, parameters={},
            reasoning=f"Ponte direta: carregar '{model_name}'",
        )
        self.logs.add_event("INFO", "DirectModelBridge", f"Carregando modelo '{model_name}' em '{runtime}'...")
        success = await self.runtime.start(runtime, plan)

        if not success:
            self.logs.add_event("ERROR", "DirectModelBridge", f"Falha ao carregar '{model_name}'.")
            return {"ok": False, "error": f"Falha ao carregar modelo '{model_name}' em '{runtime}'."}

        self.logs.add_event("INFO", "DirectModelBridge", f"Modelo '{model_name}' ativo em '{runtime}'.")
        return {"ok": True, "model": model_name, "runtime": runtime}

    async def unload_model_direct(self, runtime: str = "llama.cpp") -> dict:
        """Descarrega o modelo atualmente ativo em `runtime`, liberando
        RAM/VRAM sem carregar nada no lugar."""
        if self.runtime is None:
            return {"ok": False, "error": "RuntimeEngine não disponível (não injetado no ResidentManager)."}

        self.logs.add_event("INFO", "DirectModelBridge", f"Descarregando '{runtime}'...")
        success = await self.runtime.stop(runtime)
        if not success:
            return {"ok": False, "error": f"Falha ao descarregar '{runtime}' (talvez já estivesse parado)."}

        self.logs.add_event("INFO", "DirectModelBridge", f"'{runtime}' descarregado - memória liberada.")
        return {"ok": True, "runtime": runtime}

    # ============================================================
    # MÉTODOS DA INTERFACE (Stubs para satisfazer o contrato)
    # ============================================================

    async def get_status(self) -> dict:
        return {"status": "ONLINE", "active_mission": self._active_mission is not None}

    async def execute_plan(self, plan: dict) -> dict:
        # PHX-FIX (auditoria 2026-08-09): este método sempre devolveu
        # {"output": "Execução delegada para o Mission Kernel."} sem
        # delegar nada de verdade - é o mesmo padrão do bug de "fake
        # success" já corrigido antes no MissionExecutor, só que aqui.
        # Nada no projeto chama execute_plan() hoje (só existe pra
        # satisfazer IResidentManager), então em vez de inventar uma
        # implementação não testada que constrói um Mission() a partir de
        # um dict solto - risco real de bug silencioso pior que o stub -
        # ele agora falha de forma explícita. O fluxo real e testado pra
        # rodar uma missão continua sendo process_intent() (cria e registra
        # a missão) seguido de approve_and_execute() (aprova e dispara a
        # execução em background), exatamente como o ApiEngine já usa.
        raise NotImplementedError(
            "execute_plan() não está implementado. Use process_intent(intent) "
            "para criar e registrar uma missão, depois approve_and_execute() "
            "para aprová-la e executá-la - esse é o fluxo real e testado."
        )


def _is_image_model_target(target: str) -> bool:
    """Heurística simples: o alvo do DOWNLOAD_MODEL parece ser um modelo
    de imagem (flux/sd15/sdxl)? Usado só pra decidir se vale a pena checar
    a pasta 'Image' antes de baixar de novo."""
    if not target:
        return False
    t = target.lower()
    return any(kw in t for arch_kws in _IMAGE_ARCH_PATTERNS.values() for kw in arch_kws)