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
        
        # Verifica se a GPU tem VRAM suficiente (4GB+) e suporta Vulkan
        gpu_capable_for_llamacpp = has_gpu and vram_mb >= 4000 and 'vulkan' in backends

        # O motor LLM OFICIAL é sempre o llama.cpp
        runtime = "llama.cpp"
        model_name = "qwen3:8b"  # MODELO PADRÃO (identificador lógico)

        query = user_prompt if user_prompt else "identidade e propósito da AIVisions Platform"
        
        try:
            recommendation = await self._knowledge.query_knowledge(query)
        except Exception as e:
            logger.warning(f"RuleEvaluator: Falha ao consultar RAG ({e}), usando prompt padrão.")
            recommendation = None

        context_text = ""
        if recommendation:
            cmd = recommendation.get("command", "")
            
            # Tenta extrair o nome do modelo .gguf do comando RAG, se existir
            model_match = re.search(r'-m\s+([^\s]+\.gguf)', cmd)
            if model_match:
                model_name = model_match.group(1)
            else:
                # Se não achar .gguf no comando, tenta pegar o "name" do RAG
                rag_model = recommendation.get("name", "")
                if rag_model:
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

        # Decide a estratégia (Vulkan/GPU ou CPU fallback) baseado no hardware
        if gpu_capable_for_llamacpp:
            logger.info(f"RuleEvaluator: Executando via llama.cpp (Vulkan/GPU) com modelo {model_name}.")
            return ExecutionPlan(
                runtime='llama.cpp', 
                backend='vulkan', 
                model=model_name, 
                strategy='gpu_vulkan',
                parameters=parameters, 
                confidence=0.99, 
                reasoning="Hardware suporta Vulkan e VRAM é suficiente."
            )
        else:
            logger.info(f"RuleEvaluator: Executando via llama.cpp (CPU) com modelo {model_name}.")
            return ExecutionPlan(
                runtime='llama.cpp', 
                backend='cpu', 
                model=model_name, 
                strategy='cpu_inference',
                parameters=parameters, 
                confidence=0.8, 
                reasoning="Fallback para CPU por falta de VRAM/Vulkan adequados."
            )