from __future__ import annotations
import asyncio
import logging
import urllib.request
import json
from datetime import datetime, timezone
from typing import Any

from core.domain.execution import ExecutionPlan, ExecutionResult, ExecutionStatus
from core.domain.runtime import RuntimeStatus, RuntimeState

logger = logging.getLogger(__name__)
_UTC = timezone.utc

class OllamaDriver:
    @property
    def name(self) -> str: return "ollama"

    async def start(self) -> bool: return True
    async def stop(self) -> bool: return True

    async def status(self) -> RuntimeStatus:
        try:
            loop = asyncio.get_running_loop()
            def check():
                try:
                    with urllib.request.urlopen("http://localhost:11434/api/version", timeout=2) as r:
                        return r.status == 200
                except: return False
            is_ok = await loop.run_in_executor(None, check)
            return RuntimeStatus(name=self.name, state=RuntimeState.RUNNING if is_ok else RuntimeState.ERROR)
        except: return RuntimeStatus(name=self.name, state=RuntimeState.ERROR)

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        logger.info("OllamaDriver: Executing plan %s", plan.id)
        
        # PHX-FIX: Usando /api/chat para melhor compatibilidade com modelos instruct (Llama 3)
        payload = {
            "model": plan.model, 
            "messages": [{"role": "user", "content": plan.parameters.get("prompt", "")}], 
            "stream": False
        }
        data = json.dumps(payload).encode('utf-8')
        
        try:
            loop = asyncio.get_running_loop()
            def req():
                req = urllib.request.Request("http://localhost:11434/api/chat", data=data, headers={'Content-Type': 'application/json'})
                # PHX-FIX: Timeout aumentado para 600s (10 min) para suportar inferência pesada na CPU
                with urllib.request.urlopen(req, timeout=600) as r:
                    return json.loads(r.read().decode())
            
            res_data = await loop.run_in_executor(None, req)
            
            # A resposta do /api/chat vem dentro de message.content
            output_text = res_data.get("message", {}).get("content", "")
            
            return ExecutionResult(
                plan_id=plan.id, 
                status=ExecutionStatus.SUCCESS, 
                output=output_text,
                metrics={"tokens_per_second": res_data.get("eval_count", 0) / max(res_data.get("eval_duration", 1) / 1e9, 0.001)},
                started_at=datetime.now(_UTC), 
                finished_at=datetime.now(_UTC)
            )
        except Exception as exc:
            logger.error("OllamaDriver: Execution failed - %s", exc)
            return ExecutionResult(plan_id=plan.id, status=ExecutionStatus.FAILED, errors=[str(exc)])

    async def pull_model(self, model_name: str) -> bool:
        logger.info("OllamaDriver: Pulling model '%s'...", model_name)
        try:
            payload = {"name": model_name}
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request("http://localhost:11434/api/pull", data=data, headers={"Content-Type": "application/json"})
            loop = asyncio.get_running_loop()
            def req_exec():
                with urllib.request.urlopen(req, timeout=600) as r:
                    for line in r: pass
                return True
            return await loop.run_in_executor(None, req_exec)
        except Exception as e:
            logger.error("OllamaDriver: Failed to pull model: %s", e)
            return False

    async def embed(self, model_name: str, text: str) -> list[float]:
        try:
            payload = {"model": model_name, "prompt": text}
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request("http://localhost:11434/api/embeddings", data=data, headers={"Content-Type": "application/json"})
            loop = asyncio.get_running_loop()
            def req_exec():
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read().decode()).get("embedding", [])
            return await loop.run_in_executor(None, req_exec)
        except Exception as e:
            logger.error("OllamaDriver: Failed to generate embedding: %s", e)
            return []

    async def describe_image(self, model_name: str, prompt: str, image_path: str) -> str:
        import base64
        from pathlib import Path
        if not Path(image_path).exists(): return "Error: Image file not found."
        with open(image_path, "rb") as f: image_b64 = base64.b64encode(f.read()).decode()
        
        payload = {
            "model": model_name, 
            "messages": [{"role": "user", "content": prompt, "images": [image_b64]}], 
            "stream": False
        }
        data = json.dumps(payload).encode('utf-8')
        try:
            req = urllib.request.Request("http://localhost:11434/api/chat", data=data, headers={"Content-Type": "application/json"})
            loop = asyncio.get_running_loop()
            def req_exec():
                with urllib.request.urlopen(req, timeout=600) as r:
                    return json.loads(r.read().decode()).get("message", {}).get("content", "")
            return await loop.run_in_executor(None, req_exec)
        except Exception as e:
            logger.error("OllamaDriver: Image description failed: %s", e)
            return f"Error: {str(e)}"