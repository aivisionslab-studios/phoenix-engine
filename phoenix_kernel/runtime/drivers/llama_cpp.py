from __future__ import annotations
import asyncio
import logging
import json
import os
import urllib.request
import urllib.error
import httpx
import psutil
from pathlib import Path
from datetime import datetime, timezone

from core.domain.execution import ExecutionPlan, ExecutionResult, ExecutionStatus
from core.domain.runtime import RuntimeStatus, RuntimeState
from phoenix_kernel.paths import PhoenixPaths

logger = logging.getLogger(__name__)
_UTC = timezone.utc


def _discover_project_root(start_file: Path) -> Path:
    current = start_file.resolve()
    for _ in range(8):
        current = current.parent
        candidate = current / "repos" / "llama.cpp"
        if candidate.exists():
            return current
    return start_file.resolve().parent.parent.parent.parent


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
        if exe_path.exists() and exe_path.stat().st_size > 0:
            return str(exe_path)
        
        ninja_exe_path = self._project_root / "repos" / "llama.cpp" / "build" / "bin" / "llama-server.exe"
        if ninja_exe_path.exists() and ninja_exe_path.stat().st_size > 0:
            return str(ninja_exe_path)
            
        import shutil
        return shutil.which('llama-server') or shutil.which('main')

    def _find_model_file(self, model_name: str) -> Path | None:
        clean_name = model_name.split(":")[0].replace("/", "-").lower()
        
        def search_in_dir(dir_path: Path) -> Path | None:
            if not dir_path.exists(): return None
            matches = list(dir_path.glob(f"*{clean_name}*.gguf"))
            for match in matches:
                if match.stat().st_size > 50 * 1024 * 1024: 
                    return match
            return None

        # 1. Tenta o caminho relativo do projeto
        found = search_in_dir(PhoenixPaths.get_category_path("Chat", "GGUF"))
        if found: return found

        # 2. Tenta ler o arquivo de configuração dinâmico do sistema
        storage_candidates = []
        programdata = os.environ.get("ProgramData")
        if programdata:
            storage_candidates.append(Path(programdata) / "Phoenix" / "storage.json")
        storage_candidates.append(self._project_root / "data" / "storage.json")

        for s_path in storage_candidates:
            if s_path.exists():
                try:
                    storage = json.loads(s_path.read_text(encoding="utf-8"))
                    workspace = storage.get("workspace")
                    if workspace:
                        found = search_in_dir(Path(workspace) / "Models" / "Chat" / "GGUF")
                        if found: return found
                except Exception:
                    pass

        # 3. Se nada funcionar, varre TODOS os discos físicos conectados à máquina
        logger.info(f"LlamaCppDriver: Varrendo discos físicos para encontrar o modelo '{model_name}'...")
        for partition in psutil.disk_partitions(all=False):
            mountpoint = partition.mountpoint
            try:
                dynamic_path = Path(mountpoint) / "Phoenix" / "Workstations" / "Models" / "Chat" / "GGUF"
                found = search_in_dir(dynamic_path)
                if found: 
                    logger.info(f"LlamaCppDriver: Modelo encontrado em {dynamic_path}")
                    return found
                
                found = search_in_dir(Path(mountpoint) / "Models" / "Chat" / "GGUF")
                if found: 
                    logger.info(f"LlamaCppDriver: Modelo encontrado em {Path(mountpoint)}")
                    return found

            except PermissionError:
                continue

        logger.error(f"LlamaCppDriver: modelo '{model_name}' não encontrado em nenhum disco.")
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
        model_name = plan.model if plan and plan.model else "qwen3:8b"
        requested_model_path = self._find_model_file(model_name)

        # PHX-FIX: antes, se JÁ tivesse um processo rodando, start()
        # retornava True na hora, sem checar se era o modelo CERTO - pedir
        # pra trocar de modelo (LOAD_MODEL) nunca trocava nada de verdade,
        # só confirmava que "algum" llama-server estava de pé. Agora
        # compara o arquivo do modelo pedido com o que está carregado; só
        # reaproveita o processo se for exatamente o mesmo arquivo -
        # senão para o antigo e carrega o novo.
        if self._process and self._process.returncode is None:
            if requested_model_path and self._model_path and requested_model_path == self._model_path:
                return True  # já é o modelo certo, nada a fazer
            logger.info(
                f"LlamaCppDriver: troca de modelo pedida "
                f"('{self._model_path.name if self._model_path else '?'}' -> '{model_name}') - recarregando."
            )
            await self.stop()

        if not requested_model_path:
            logger.error(f"LlamaCppDriver: modelo '{model_name}' não encontrado em nenhum disco.")
            return False
        model_path = requested_model_path

        exe_path = self._find_executable()
        if not exe_path:
            logger.error("LlamaCppDriver: BINARIO llama-server NAO ENCONTRADO.")
            return False

        self._model_path = model_path
        
        ngl = os.environ.get("PHOENIX_LLM_NGL", "0")
        logger.info(f"LlamaCppDriver: Iniciando motor nativo. Modelo: {model_path.name}, NGL: {ngl}")

        try:
            env = os.environ.copy()
            cwd = str(Path(exe_path).parent)

            # PHX-FIX: Contexto aumentado para 8192 para evitar Erro 500 (Context size exceeded)
            self._process = await asyncio.create_subprocess_exec(
                exe_path, '-m', str(model_path), '--host', '127.0.0.1', '--port', str(self._port), 
                '-ngl', ngl, '--no-op-offload', '-c', '8192',
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE, env=env, cwd=cwd
            )
            
            for _ in range(120):
                if await self._check_health(): return True
                if self._process.returncode is not None:
                    stderr_data = await self._process.stderr.read()
                    err_msg = stderr_data.decode('utf-8', errors='replace').strip()
                    logger.error(f"LlamaCppDriver: Processo morreu. STDERR do llama-server: {err_msg[-500:]}")
                    return False
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

        model_label = self._model_path.name if self._model_path else "?"
        preview = prompt[:120] + ("..." if len(prompt) > 120 else "")
        logger.info(f"LlamaCppDriver: Enviando prompt para '{model_label}' via HTTP: \"{preview}\"")

        payload = {
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            "max_tokens": params.get("max_tokens", 1024), "temperature": params.get("temperature", 0.1)
        }

        # PHX-FIX: started_at precisa ser capturado ANTES da chamada HTTP,
        # não depois - antes disso, started_at e finished_at eram gerados
        # na mesma linha, os dois DEPOIS da resposta já ter voltado, então
        # a duração real da inferência (que pode levar minutos em CPU)
        # nunca era capturada - sempre dava ~0ms.
        started_at = datetime.now(_UTC)

        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(
                    f'http://127.0.0.1:{self._port}/v1/chat/completions',
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()
                res_data = response.json()

            finished_at = datetime.now(_UTC)
            output_text = res_data.get("choices", [{}])[0].get("message", {}).get("content", "")

            # PHX-NEW: o llama-server (endpoint compatível OpenAI) já
            # devolve "usage" com completion_tokens/prompt_tokens - isso
            # era descartado antes, só output_text era extraído. Sem isso,
            # ExecutionResult.metrics ficava sempre vazio e não dava pra
            # saber tokens/s de nenhuma execução real.
            usage = res_data.get("usage") or {}
            completion_tokens = usage.get("completion_tokens", 0)
            elapsed_s = (finished_at - started_at).total_seconds()
            tokens_per_second = round(completion_tokens / elapsed_s, 2) if elapsed_s > 0 and completion_tokens else 0.0

            return ExecutionResult(
                plan_id=plan.id, status=ExecutionStatus.SUCCESS, output=output_text,
                metrics={
                    "tokens_generated": completion_tokens,
                    "tokens_per_second": tokens_per_second,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "duration_ms": round(elapsed_s * 1000),
                },
                started_at=started_at, finished_at=finished_at,
            )

        except Exception as exc:
            return ExecutionResult(plan_id=plan.id, status=ExecutionStatus.FAILED, errors=[f"Erro na inferência do llama.cpp: {str(exc)}"])
