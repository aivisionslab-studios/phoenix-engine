from __future__ import annotations
import logging
import re
from core.domain.machine import MachineContext
from core.domain.execution import ExecutionPlan

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Você é a Phoenix, o motor de orquestração de IA da AIVisions Platform 3.0 — "
    "um projeto de 'Hardware Revival': provar que GPUs e CPUs consideradas "
    "obsoletas pelo mercado (como a RX 580, um Xeon de servidor antigo) ainda "
    "têm gás pra rodar IA moderna, sem CUDA, sem ROCm, só com Vulkan e "
    "engenharia teimosa. Você fala como alguém que genuinamente curte esse "
    "tipo de desafio — entusiasmado com hardware velho fazendo coisa grande, "
    "com senso de humor seco de quem já apanhou de driver quebrado às 3 da "
    "manhã e sobreviveu. Pode brincar, fazer graça, soltar uma piada sobre "
    "o barulho do cooler ou sobre placas de vídeo 'aposentadas' que ainda "
    "trabalham mais que muita GPU nova.\n\n"
    "Mas ATENÇÃO — isso nunca pode custar precisão técnica:\n"
    "- Nunca invente números de hardware (VRAM, tokens/s, temperatura). Se não tiver a informação exata no contexto abaixo, diga abertamente 'não tenho esse dado exato aqui'.\n"
    "- Nunca invente funcionalidades, telas, botões ou comandos da AIVisions Platform que não estejam descritos no contexto.\n"
    "- Se o contexto do projeto abaixo não for relevante para a pergunta, ignore-o e responda com seu conhecimento geral, deixando claro que é conhecimento geral.\n"
    "- Precisão técnica sempre vem antes de graça. Divirta-se com o tom, nunca com o fato."
)

_KNOWN_OLLAMA_MODELS = {
    "qwen3:8b", "llama3.2:3b", "llama3.2:1b", "llama3.1:8b", "llama3:latest",
    "qwen2.5:7b", "qwen2.5:3b", "nomic-embed-text",
}

def _is_valid_ollama_model(name: str) -> bool:
    if not name: return False
    if name in _KNOWN_OLLAMA_MODELS: return True
    if " " in name or len(name) > 60: return False
    return bool(re.match(r'^[a-zA-Z0-9._\-]+(:[a-zA-Z0-9._\-]+)?$', name))

class RuleEvaluator:
    def __init__(self, knowledge_engine):
        self._knowledge = knowledge_engine

    async def evaluate(self, context: MachineContext, user_prompt: str = "") -> ExecutionPlan:
        if not context.profile:
            return ExecutionPlan(strategy='fallback', reasoning='No hardware profile.')

        gpus = context.profile.gpus
        has_gpu = len(gpus) > 0
        vram_mb = gpus[0].get('vram_mb', 0) if has_gpu else 0
        backends = context.profile.available_backends
        gpu_capable_for_llamacpp = has_gpu and vram_mb >= 4000 and 'vulkan' in backends

        # RAG é consultado SEMPRE, independente do hardware.
        context_text = ""
        runtime = "ollama"
        model_name = "qwen3:8b"  # MODELO OFICIAL PADRÃO

        query = user_prompt if user_prompt else "identidade e propósito da AIVisions Platform"
        recommendation = await self._knowledge.query_knowledge(query)

        if recommendation:
            cmd = recommendation.get("command", "")
            # Só usa llama.cpp se o HARDWARE aguentar E o doc tiver comando llama.cpp
            if gpu_capable_for_llamacpp and ("llama-server" in cmd or "llama-cli" in cmd):
                runtime = "llama.cpp"
                model_match = re.search(r'-m\s+([^\s]+\.gguf)', cmd)
                if model_match:
                    model_name = model_match.group(1)
            else:
                rag_model = recommendation.get("name", "")
                if _is_valid_ollama_model(rag_model):
                    model_name = rag_model

            context_text = (
                recommendation.get("description", "") or
                recommendation.get("notes", "") or
                recommendation.get("solution", "")
            )
            if context_text:
                logger.info("RuleEvaluator: Contexto RAG injetado no prompt com sucesso.")

        final_prompt = f"{SYSTEM_PROMPT}\n\n"
        if context_text:
            final_prompt += f"Contexto do Projeto (use apenas se for estritamente relevante para a pergunta):\n{context_text}\n\n"
        final_prompt += f"Pergunta do Usuário: {user_prompt}"

        parameters = {'prompt': final_prompt, 'max_tokens': 300}

        if runtime == "llama.cpp":
            logger.info(f"RuleEvaluator: Executando via llama.cpp com modelo {model_name}.")
            return ExecutionPlan(
                runtime='llama.cpp', backend='vulkan', model=model_name, strategy='gpu_vulkan',
                parameters=parameters, confidence=0.99, reasoning="RAG recomendou e hardware suporta"
            )
        else:
            logger.info(f"RuleEvaluator: Executando via Ollama com modelo {model_name}.")
            return ExecutionPlan(
                runtime='ollama', backend='cpu', model=model_name, strategy='cpu_inference',
                parameters=parameters, confidence=0.8, reasoning="Fallback Ollama"
            )