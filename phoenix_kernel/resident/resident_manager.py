import asyncio
import logging
import importlib
import re
import time
from datetime import datetime, timezone

from .interfaces import IResidentManager
from phoenix_kernel.intelligence.reasoning_engine import ReasoningEngine
from phoenix_kernel.core.enums import MissionStatus, MissionAction
from core.domain.execution import ExecutionPlan, ExecutionStatus

logger = logging.getLogger(__name__)

_hardware_core = importlib.import_module("phoenix_kernel.telemetry.core")
_models_module = importlib.import_module("phoenix_kernel.models.model_manager")
_paths_module = importlib.import_module("phoenix_kernel.paths")
ModelManager = _models_module.ModelManager
PhoenixPaths = _paths_module.PhoenixPaths

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
    def __init__(self, state_engine, planner_engine, services_engine, logs_engine, runtime_engine=None, model_manager=None):
        self.state = state_engine
        self.planner = planner_engine
        self.services = services_engine
        self.logs = logs_engine
        self.runtime = runtime_engine

        # PHX-FIX: Injeta runtime_engine E logs_engine no ReasoningEngine - o
        # runtime pra usar o driver nativo (Vulkan), os logs pra você ver o
        # "pensamento" ao vivo no painel em vez do terminal ficar mudo.
        self.reasoning = ReasoningEngine(state_engine, runtime_engine=self.runtime, logs_engine=self.logs)

        # PHX-FIX: Usa o ModelManager injetado pelo Kernel ou cria um fallback
        self.model_manager = model_manager if model_manager else ModelManager()

        self._active_mission = None

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
        recommendation = await self.planner.knowledge.query_knowledge(query)

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
        if recommendation:
            report += "Baseado em testes anteriores, recomenda-se:\n"
            report += f"- {recommendation.get('name', 'N/A')}\n"
            report += f"- Notas: {recommendation.get('notes', 'N/A')}\n"
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
    # INTEGRAÇÃO REASONING ENGINE (O CÉREBRO)
    # ============================================================

    async def process_intent(self, intent: str) -> dict:
        """Recebe a intenção do usuário, pede ao LLM para pensar e devolve o plano."""
        mission = await self.reasoning.plan_mission(intent)

        if not mission:
            # PHX-FIX: Expõe o motivo real (guardado pelo ReasoningEngine em
            # last_error) em vez da mensagem genérica que escondia se o
            # llama-cli realmente falhou, deu timeout, ou devolveu algo que
            # não era JSON.
            detail = getattr(self.reasoning, "last_error", None) or "motivo desconhecido"
            return {"output": f"[ERRO] O cérebro (LLM) não respondeu: {detail}"}

        self._active_mission = mission

        return {
            "output": f"Plano criado: {mission.metadata.get('llm_reasoning', '')}\nAguardando aprovação.",
            "mission": mission.to_dict()
        }

    async def approve_and_execute(self) -> dict:
        """Aprova a missão pendente e aciona a execução em Background."""
        if not self._active_mission:
            return {"output": "Nenhuma missão pendente para aprovação."}

        mission = self._active_mission
        mission.status = MissionStatus.RUNNING

        # Dispara a execução em segundo plano para não travar o terminal do painel
        asyncio.create_task(self._execute_mission_background(mission))

        self._active_mission = None

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

        resolved_model, resolution_note = self._resolve_image_model_target(model_hint or "flux")
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
    # MÉTODOS DA INTERFACE (Stubs para satisfazer o contrato)
    # ============================================================

    async def get_status(self) -> dict:
        return {"status": "ONLINE", "active_mission": self._active_mission is not None}

    async def execute_plan(self, plan: dict) -> dict:
        return {"output": "Execução delegada para o Mission Kernel."}


def _is_image_model_target(target: str) -> bool:
    """Heurística simples: o alvo do DOWNLOAD_MODEL parece ser um modelo
    de imagem (flux/sd15/sdxl)? Usado só pra decidir se vale a pena checar
    a pasta 'Image' antes de baixar de novo."""
    if not target:
        return False
    t = target.lower()
    return any(kw in t for arch_kws in _IMAGE_ARCH_PATTERNS.values() for kw in arch_kws)