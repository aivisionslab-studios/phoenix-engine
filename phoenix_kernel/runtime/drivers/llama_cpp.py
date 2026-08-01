from __future__ import annotations
import asyncio
import logging
import json
import os
import urllib.request
import urllib.error
import httpx
from pathlib import Path
from datetime import datetime, timezone

from core.domain.execution import ExecutionPlan, ExecutionResult, ExecutionStatus
from core.domain.runtime import RuntimeStatus, RuntimeState
from phoenix_kernel.paths import PhoenixPaths

logger = logging.getLogger(__name__)
_UTC = timezone.utc


def _discover_project_root(start_file: Path) -> Path:
    """
    PHX-FIX: mesmo padrão de descoberta usado no SdCppDriver. Em vez de
    contar '.parent' no escuro (frágil - quebra se o arquivo mudar de
    lugar), sobe a árvore de diretórios procurando 'repos/llama.cpp'.
    Se não achar, cai no cálculo antigo (4 parents) e AVISA no log, pra
    não falhar silenciosamente igual acontecia antes no sd_cpp.py.
    """
    current = start_file.resolve()
    for _ in range(8):
        current = current.parent
        candidate = current / "repos" / "llama.cpp"
        if candidate.exists():
            logger.info(f"LlamaCppDriver: raiz do projeto encontrada em '{current}' (achou '{candidate}')")
            return current
    fallback = start_file.resolve().parent.parent.parent.parent
    logger.warning(
        f"LlamaCppDriver: NAO achei 'repos/llama.cpp' subindo a arvore a partir de "
        f"'{start_file}'. Usando fallback '{fallback}'."
    )
    return fallback


class LlamaCppDriver:
    def __init__(self, *args, **kwargs) -> None:
        self._project_root = _discover_project_root(Path(__file__))
        self._process = None
        self._port = 8081
        self._model_path = None

    @property
    def name(self) -> str: 
        return 'llama.cpp'

    def _find_executable(self) -> str | None:
        exe_path = self._project_root / "repos" / "llama.cpp" / "build" / "bin" / "Release" / "llama-server.exe"
        if exe_path.exists():
            return str(exe_path)
        import shutil
        found = shutil.which('llama-server') or shutil.which('main')
        if not found:
            logger.error(
                f"LlamaCppDriver: llama-server.exe NAO encontrado em '{exe_path}' "
                f"nem no PATH do sistema. project_root='{self._project_root}'."
            )
        return found

    def _find_model_file(self, model_name: str) -> Path | None:
        clean_name = model_name.split(":")[0].replace("/", "-").lower()
        models_dir = PhoenixPaths.get_category_path("Chat", "GGUF")
        if not models_dir.exists(): return None
        matches = list(models_dir.glob(f"*{clean_name}*.gguf"))
        for match in matches:
            if match.stat().st_size > 50 * 1024 * 1024: return match
        return None

    async def _check_health(self) -> bool:
        try:
            def check():
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{self._port}/health", timeout=2) as r:
                        return r.status == 200
                except: return False
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, check)
        except: return False

    async def start(self, plan: ExecutionPlan | None = None) -> bool:
        if self._process and self._process.returncode is None: return True
            
        model_name = plan.model if plan and plan.model else "qwen3:8b"
        model_path = self._find_model_file(model_name)
        if not model_path:
            logger.error(f"LlamaCppDriver: modelo '{model_name}' nao encontrado em Chat/GGUF.")
            return False

        exe_path = self._find_executable()
        if not exe_path: return False

        self._model_path = model_path
        
        # PHX-FIX: Política de hardware do projeto - LLM/chatbot SEMPRE roda
        # em CPU (usando RAM, não VRAM). Motivo: alternar CPU<->GPU<->split
        # híbrido dá trabalho real (prompts, comandos e testes diferentes
        # em Windows/Linux) e a VRAM da RX 580 fica reservada pra geração
        # de imagem, que é ordens de magnitude mais pesada. Isso NÃO é
        # fallback nem detecção de ausência de GPU - é decisão de arquitetura.
        ngl = os.environ.get("PHOENIX_LLM_NGL", "0")
        logger.info(f"LlamaCppDriver: Iniciando motor nativo (Server). Modelo: {model_path.name}, NGL: {ngl} (CPU Policy)")

        try:
            env = os.environ.copy()
            cwd = str(Path(exe_path).parent)

            # PHX-FIX: "-ngl 0" sozinho NÃO garante CPU-only. O llama.cpp
            # tem "--op-offload" ativado por padrão (default: true), que
            # deixa o scheduler empurrar operações individuais (matmuls do
            # processamento de prompt) pra GPU mesmo com 0 camadas
            # offloaded - é o comportamento que a gente via a RX 580
            # "ajudando por debaixo dos panos" mesmo com ngl=0. Adicionar
            # "--no-op-offload" fecha essa porta e deixa o motor 100% CPU,
            # como a política do projeto pede.
            self._process = await asyncio.create_subprocess_exec(
                exe_path, '-m', str(model_path), '--host', '127.0.0.1', '--port', str(self._port), 
                '-ngl', ngl, '--no-op-offload', '-c', '4096', '--reasoning-budget', '0',
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE, env=env, cwd=cwd
            )
            
            for _ in range(120):
                if await self._check_health(): return True
                if self._process.returncode is not None: return False
                await asyncio.sleep(1)
            return False
        except Exception as exc:
            logger.error(f"LlamaCppDriver: erro inesperado ao iniciar - {exc}")
            return False

    async def stop(self) -> bool:
        if self._process and self._process.returncode is None:
            self._process.terminate()
            await self._process.wait()
        self._process = None
        return True

    async def status(self) -> RuntimeStatus:
        if self._process and self._process.returncode is None:
            return RuntimeStatus(name=self.name, state=RuntimeState.RUNNING if await self._check_health() else RuntimeState.ERROR)
        return RuntimeStatus(name=self.name, state=RuntimeState.STOPPED)

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        if not await self._check_health():
            if not await self.start(plan):
                return ExecutionResult(plan_id=plan.id, status=ExecutionStatus.FAILED, errors=["Failed to start llama.cpp server"])

        params = plan.parameters or {}
        prompt = params.get("user_prompt", params.get("prompt", ""))
        system_prompt = params.get("system_prompt", "Você é um assistente útil.")

        # PHX-FIX: log de paridade com o SdCppDriver (que já loga o comando
        # inteiro antes de rodar). O prompt aqui viaja como JSON via httpx,
        # então NÃO sofre o bug de codepage do Windows que afeta argv de
        # linha de comando (acentos/UTF-8 preservados nativamente) - mas
        # sem esse log, um prompt vazio ou truncado por engano no plano da
        # missão passava batido até a resposta do modelo já sair estranha.
        model_label = self._model_path.name if self._model_path else "?"
        preview = prompt[:120] + ("..." if len(prompt) > 120 else "")
        logger.info(f"LlamaCppDriver: Enviando prompt para '{model_label}' via HTTP (porta {self._port}): \"{preview}\"")

        payload = {
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            "max_tokens": params.get("max_tokens", 1024), "temperature": params.get("temperature", 0.1)
        }
        
        try:
            # PHX-FIX: Trocado urllib por httpx assíncrono para não travar o Event Loop do FastAPI.
            # Timeout aumentado para 600s (10 min) para dar tempo da CPU gerar respostas longas sem cancelar.
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(
                    f'http://127.0.0.1:{self._port}/v1/chat/completions',
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()
                res_data = response.json()

            output_text = res_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return ExecutionResult(plan_id=plan.id, status=ExecutionStatus.SUCCESS, output=output_text, started_at=datetime.now(_UTC), finished_at=datetime.now(_UTC))
            
        except Exception as exc:
            return ExecutionResult(plan_id=plan.id, status=ExecutionStatus.FAILED, errors=[f"Erro na inferência do llama.cpp: {str(exc)}"])
