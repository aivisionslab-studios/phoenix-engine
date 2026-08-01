import json
import logging
import asyncio
from phoenix_kernel.core.models import Mission, MissionStep
from phoenix_kernel.core.enums import MissionAction, MissionStatus
from phoenix_kernel.intelligence.web_search import search_web
from phoenix_kernel.intelligence.knowledge_engine import KnowledgeEngine
from core.domain.execution import ExecutionPlan, ExecutionStatus

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "qwen3:8b"

# O System Prompt agora é mais limpo. A identidade e as regras de hardware
# vêm do KnowledgeEngine (intrinsic/phoenix_identity.md).
SYSTEM_PROMPT = """Você é o Phoenix OS, o cérebro orquestrador de uma plataforma de IA local.
Sua função é analisar o pedido do usuário e o contexto fornecido, e criar um PLANO DE AÇÃO (Mission).
Você NÃO executa comandos. Você apenas desenha o plano em formato JSON.

Ferramentas (Actions) que você pode usar:
- VALIDATE_ENVIRONMENT: Checar se um software (target) está pronto (ex: target="docker").
- INSTALL_PACKAGE: Instalar um PACOTE DE SOFTWARE (target="ollama", target="stable-diffusion.cpp", target="comfyui").
- DOWNLOAD_MODEL: Baixar um ARQUIVO .gguf de um modelo de IA (target="qwen3:8b", target="flux").
- SWITCH_RUNTIME: Trocar o motor de inferência de TEXTO (target="llama.cpp" para usar Vulkan/GPU, target="ollama" para usar CPU).
- GENERATE_IMAGE: Rodar a inferência de um modelo de IMAGEM já baixado (target=id do modelo no catálogo, ex: "flux", "sdxl", "sd15"; parameters={"prompt": "..."}).

REGRA CRÍTICA DE GERAÇÃO DE IMAGEM:
- DOWNLOAD_MODEL sozinho NUNCA gera uma imagem - ele só baixa o arquivo .gguf pro disco. Se o usuário quer VER/CRIAR uma imagem (não só instalar o ambiente), o plano PRECISA terminar com um passo GENERATE_IMAGE, senão a missão "termina" sem nunca ter rodado nada na GPU.
- Sequência correta para pedidos de imagem: VALIDATE_ENVIRONMENT(docker) -> INSTALL_PACKAGE(stable-diffusion.cpp) -> DOWNLOAD_MODEL(flux ou outro) -> GENERATE_IMAGE(mesmo target do DOWNLOAD_MODEL, com um prompt em parameters).
- Se o usuário não descreveu o que quer na imagem, use um prompt de teste simples em parameters (ex: "a red apple on a wooden table, photorealistic") só para validar que o pipeline e a GPU estão funcionando - não deixe o passo faltando.

REGRA CRÍTICA DE AÇÕES (NUNCA CONFUNDA):
- INSTALL_PACKAGE é apenas para instalar SOFTWARE (ex: stable-diffusion.cpp, comfyui).
- DOWNLOAD_MODEL é apenas para baixar ARQUIVOS .gguf de modelos de IA (ex: flux, qwen3:8b).
- NUNCA use DOWNLOAD_MODEL para baixar software. Software é instalado via INSTALL_PACKAGE.
- O llama.cpp JÁ ESTÁ INSTALADO E COMPILADO COM VULKAN durante o bootstrap da Phoenix. NUNCA sugira INSTALL_PACKAGE ou DOWNLOAD_MODEL para "llama.cpp". Se quiser usar a GPU nativa, use apenas SWITCH_RUNTIME com target="llama.cpp".
- Se o modelo qwen3:8b já está baixado e rodando no Ollama, NÃO sugira DOWNLOAD_MODEL para ele.

REGRA DE HARDWARE CRÍTICA:
- Se a GPU for AMD (como RX 580 / Polaris) e o backend for Vulkan, NUNCA sugira ComfyUI, AUTOMATIC1111 ou Forge (eles dependem de PyTorch/CUDA/ROCm, que não funcionam em Polaris).
- Para geração de imagens em AMD Legacy, SEMPRE use o target="stable-diffusion.cpp" (via INSTALL_PACKAGE).

Regras Gerais:
1. Seja eficiente. Não instale o que já está instalado.
2. Responda SEMPRE com um JSON válido contendo "reasoning" e "steps".
3. O JSON deve ser estritamente no formato pedido.

Exemplo de Resposta (texto):
{
  "reasoning": "O usuário quer rodar IA local. A máquina tem GPU. Vou validar o Docker, instalar o Ollama e baixar o modelo.",
  "steps": [
    {"action": "VALIDATE_ENVIRONMENT", "target": "docker", "description": "Checar se o Docker está ativo"},
    {"action": "INSTALL_PACKAGE", "target": "ollama", "description": "Instalar o runtime do Ollama via Docker"},
    {"action": "DOWNLOAD_MODEL", "target": "qwen3:8b", "description": "Baixar o modelo Qwen 3 8B para inferência"}
  ]
}

Exemplo de Resposta (imagem - repare que termina em GENERATE_IMAGE, não em DOWNLOAD_MODEL):
{
  "reasoning": "O usuário quer gerar imagens localmente. GPU é AMD/Polaris, então uso stable-diffusion.cpp com Flux.",
  "steps": [
    {"action": "VALIDATE_ENVIRONMENT", "target": "docker", "description": "Checar se o Docker está ativo"},
    {"action": "INSTALL_PACKAGE", "target": "stable-diffusion.cpp", "description": "Instalar o stable-diffusion.cpp compilado com Vulkan"},
    {"action": "DOWNLOAD_MODEL", "target": "flux", "description": "Baixar o modelo Flux para geração de imagens"},
    {"action": "GENERATE_IMAGE", "target": "flux", "description": "Gerar a imagem pedida pelo usuário", "parameters": {"prompt": "a red apple on a wooden table, photorealistic"}}
  ]
}
"""


class ReasoningEngine:
    def __init__(self, state_engine=None, runtime_engine=None, logs_engine=None):
        self.state = state_engine
        self.runtime = runtime_engine
        # PHX-FIX: log estruturado (Mission Control "logs") para acompanhar o
        # "pensamento" ao vivo - sem isso o terminal fica mudo por até ~1min
        # (busca web + RAG + inferência) e parece travado.
        self.logs = logs_engine
        # PHX-FIX: guarda o motivo real de falha para o ResidentManager expor
        # em vez da mensagem genérica "cérebro não respondeu".
        self.last_error: str | None = None
        # Inicializa o KnowledgeEngine apontando para as pastas reais
        self.knowledge = KnowledgeEngine(
            knowledge_root="phoenix_kernel/knowledge",
            rag_root="phoenix_kernel/rag/source_docs"
        )

    def _log(self, level: str, msg: str) -> None:
        """Espelha no logger padrão e, se disponível, no logs_engine (visível
        ao vivo no painel) - sem quebrar se logs_engine não foi injetado."""
        getattr(logger, level.lower(), logger.info)(f"[Reasoning] {msg}")
        if self.logs:
            try:
                self.logs.add_event(level.upper(), "ReasoningEngine", msg)
            except Exception:
                pass  # logging nunca pode derrubar o raciocínio em si

    def _get_hardware_context(self) -> str:
        if not self.state:
            return "Hardware info indisponível."
        try:
            hw = self.state.get_state_sync().get("hardware", {})
            budget = self.state.get_state_sync().get("budget", {})
            return f"CPU: {hw.get('cpu', 'Unknown')}, RAM: {hw.get('ram_mb', 0)}MB, GPU: {hw.get('gpu', 'None')} ({hw.get('vram_mb', 0)}MB VRAM), Classe: {budget.get('class', 'Unknown')}"
        except Exception:
            return "Hardware em inicialização."

    async def plan_mission(self, user_intent: str):
        self._log("INFO", f"Pensando sobre: '{user_intent}'...")
        hw_context = self._get_hardware_context()

        # 1. Busca contexto na internet
        self._log("INFO", "Buscando contexto na internet...")
        web_context = await search_web(user_intent, max_results=2)

        # 2. Busca no KnowledgeEngine (Intrinsic + Machine + Procedures + RAG)
        # Roda em thread separada porque leitura de arquivos/RAG é bloqueante
        self._log("INFO", "Consultando a base de conhecimento (RAG)...")
        loop = asyncio.get_running_loop()
        knowledge_context = await loop.run_in_executor(None, self.knowledge.build_context, user_intent)

        # 3. Monta o prompt final com todas as fontes
        user_prompt = (
            f"Contexto da Máquina:\n{hw_context}\n\n"
            f"Contexto de Conhecimento (Identidade, Hardware, Receitas):\n{knowledge_context}\n\n"
            f"Contexto da Internet (use se for útil):\n{web_context}\n\n"
            f"Intenção do Usuário: {user_intent}"
        )

        if not self.runtime:
            self.last_error = "RuntimeEngine não injetado no ResidentManager."
            self._log("ERROR", self.last_error)
            return None

        # PHX-FIX: Em vez de HTTP direto para Ollama, usa o RuntimeEngine (Vulkan nativo)
        llm_plan = ExecutionPlan(
            runtime="llama.cpp",
            model=DEFAULT_MODEL,
            parameters={
                "system_prompt": SYSTEM_PROMPT,
                "user_prompt": user_prompt,
                "json_format": True
            },
            reasoning="Gerar plano de missão em JSON"
        )

        try:
            self._log("INFO", f"Consultando o cérebro nativo ({llm_plan.model} via llama.cpp)...")
            loop_start = loop.time()
            result = await self.runtime.execute(llm_plan)
            elapsed = loop.time() - loop_start

            if result.status != ExecutionStatus.SUCCESS:
                self.last_error = "; ".join(result.errors) if result.errors else "erro desconhecido"
                self._log("ERROR", f"Runtime falhou ao gerar plano ({elapsed:.1f}s): {self.last_error}")
                return None

            self._log("INFO", f"Resposta do cérebro recebida em {elapsed:.1f}s.")
            content = result.output
            logger.info(f"[Reasoning] Resposta bruta do LLM: {content}")

            plan = json.loads(content)
            reasoning = plan.get("reasoning", "Sem explicação.")
            raw_steps = plan.get("steps", [])

            if not raw_steps:
                self.last_error = "JSON válido, mas sem 'steps'."
                self._log("ERROR", self.last_error)
                return None

            steps = []
            for i, s in enumerate(raw_steps, 1):
                action_str = s.get("action", "VALIDATE_ENVIRONMENT").upper()
                try:
                    action_enum = MissionAction(action_str)
                except ValueError:
                    logger.warning(f"[Reasoning] Ação '{action_str}' inválida. Usando VALIDATE_ENVIRONMENT.")
                    action_enum = MissionAction.VALIDATE_ENVIRONMENT

                steps.append(MissionStep(
                    step=i,
                    action=action_enum,
                    target=s.get("target", "unknown"),
                    description=s.get("description", ""),
                    parameters=s.get("parameters", {}) or {},
                ))

            mission = Mission(
                intent=user_intent,
                status=MissionStatus.CREATED,
                steps=steps,
                metadata={"llm_reasoning": reasoning}
            )
            self._log("INFO", f"Missão criada com {len(steps)} passo(s).")
            return mission

        except json.JSONDecodeError:
            self.last_error = "Resposta do LLM não é um JSON válido."
            self._log("ERROR", self.last_error)
            return None
        except Exception as e:
            self.last_error = f"{type(e).__name__}: {str(e)}"
            self._log("ERROR", f"Falha inesperada: {self.last_error}")
            return None