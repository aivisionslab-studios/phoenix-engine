from __future__ import annotations
import asyncio
import logging
import shutil
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from core.domain.execution import ExecutionPlan, ExecutionResult, ExecutionStatus
from core.domain.runtime import RuntimeStatus, RuntimeState

logger = logging.getLogger(__name__)
_UTC = timezone.utc

class LlamaCppDriver:
    def __init__(self) -> None:
        self._process = None
        self._port = 8080
        self._exe = shutil.which('llama-server') or shutil.which('main')

    @property
    def name(self) -> str: return 'llama.cpp'

    # PHX-FIX: plan agora é OPCIONAL. O RuntimeEngine pode chamar start()
    # genérico (sem plan) via watchdog, ou passando o plan (durante execute)
    async def start(self, plan: ExecutionPlan | None = None) -> bool:
        if self._process and self._process.returncode is None: return True
        if not self._exe:
            logger.warning('LlamaCppDriver: llama-server/main executable not found in PATH.')
            return False

        # LÊ O MODELO DO PLANO (se não tiver plano, usa tinyllama como padrão)
        model_name = plan.model if plan and plan.model else 'tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf'
        model_path = Path(f'data/models/{model_name}')
        
        if not model_path.exists():
            logger.warning('LlamaCppDriver: Model %s not found.', model_path)
            return False

        logger.info('LlamaCppDriver: Starting server on port %s with Vulkan...', self._port)
        try:
            self._process = await asyncio.create_subprocess_exec(
                self._exe, '-m', str(model_path), '--port', str(self._port), '-ngl', '99', '-c', '2048',
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            for _ in range(15):
                if await self._check_health(): return True
                await asyncio.sleep(1)
            return False
        except Exception as exc:
            logger.error('LlamaCppDriver: Failed to start: %s', exc)
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
                return ExecutionResult(plan_id=plan.id, status=ExecutionStatus.FAILED, errors=['Failed to start llama.cpp server'])

        prompt = plan.parameters.get('prompt', '')
        payload = {'prompt': prompt, 'n_predict': plan.parameters.get('max_tokens', 50), 'temperature': 0.7}
        data = json.dumps(payload).encode('utf-8')
        
        try:
            loop = asyncio.get_running_loop()
            def req():
                req = urllib.request.Request(f'http://localhost:{self._port}/completion', data=data, headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.loads(r.read().decode())
            
            res_data = await loop.run_in_executor(None, req)
            return ExecutionResult(
                plan_id=plan.id, status=ExecutionStatus.SUCCESS, output=res_data.get('content', ''),
                metrics={'tokens_per_second': res_data.get('timings', {}).get('predicted_per_second', 0.0)},
                started_at=datetime.now(_UTC), finished_at=datetime.now(_UTC)
            )
        except Exception as exc:
            return ExecutionResult(plan_id=plan.id, status=ExecutionStatus.FAILED, errors=[str(exc)])

    async def _check_health(self) -> bool:
        try:
            def check():
                try:
                    with urllib.request.urlopen(f'http://localhost:{self._port}/health', timeout=2) as r: return r.status == 200
                except: return False
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, check)
        except: return False