# phoenix_kernel/runtime/drivers/piper.py

from __future__ import annotations

import asyncio
import logging
import platform
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timezone

from core.domain.execution import ExecutionPlan, ExecutionResult, ExecutionStatus
from core.domain.runtime import RuntimeStatus, RuntimeState
from phoenix_kernel.paths import PhoenixPaths

logger = logging.getLogger(__name__)
_UTC = timezone.utc

DEFAULT_VOICE = "pt_BR-faber-medium"


class PiperDriver:
    def __init__(self, *args, **kwargs) -> None:
        self._project_root = Path(__file__).resolve().parent.parent.parent.parent

    @property
    def name(self) -> str:
        return "piper"

    def _find_executable(self) -> str | None:
        repo_dir = self._project_root / "repos" / "Piper"
        exe_names = ["piper.exe", "piper"] if platform.system() == "Windows" else ["piper"]
        for name in exe_names:
            candidates = [repo_dir / name, repo_dir / "bin" / name]
            for c in candidates:
                if c.exists():
                    return str(c)
        return None

    def _find_voice_file(self, voice_hint: str) -> Path | None:
        try:
            voice_dir = PhoenixPaths.get_category_path("Voice", "Piper")
        except Exception:
            return None

        if not voice_dir.exists():
            return None

        # Tenta achar a voz exata primeiro
        onnx_file = voice_dir / f"{voice_hint}.onnx"
        if onnx_file.exists():
            return onnx_file

        # Se não achar exata, pega a primeira .onnx disponível
        matches = list(voice_dir.glob("*.onnx"))
        return matches[0] if matches else None

    async def start(self, plan: ExecutionPlan | None = None) -> bool:
        return self._find_executable() is not None

    async def stop(self) -> bool:
        return True

    async def status(self) -> RuntimeStatus:
        state = RuntimeState.RUNNING if self._find_executable() else RuntimeState.STOPPED
        return RuntimeStatus(name=self.name, state=state)

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        exe_path = self._find_executable()
        if not exe_path:
            return ExecutionResult(
                plan_id=plan.id,
                status=ExecutionStatus.FAILED,
                errors=["piper.exe não encontrado. Baixe o binário oficial."]
            )

        voice_hint = plan.model if plan.model else DEFAULT_VOICE
        voice_path = self._find_voice_file(voice_hint)
        if not voice_path:
            return ExecutionResult(
                plan_id=plan.id,
                status=ExecutionStatus.FAILED,
                errors=[f"Voz '{voice_hint}' não encontrada no disco."]
            )

        text = plan.parameters.get("text", "")
        if not text:
            return ExecutionResult(
                plan_id=plan.id,
                status=ExecutionStatus.FAILED,
                errors=["Texto vazio para síntese."]
            )

        # PHX-FIX: Resolve o caminho do espeak-ng-data que vem junto no ZIP do Piper
        piper_dir = Path(exe_path).parent
        espeak_data_path = piper_dir / "espeak-ng-data"
        
        temp_dir = Path(tempfile.gettempdir())
        out_wav = temp_dir / f"piper_out_{uuid.uuid4()}.wav"

        # PHX-FIX: --espeak_data garante que o Piper ache os fonemas no Windows sem instalar nada global
        cmd = [
            exe_path,
            "-m", str(voice_path),
            "-f", str(out_wav),
            "--espeak_data", str(espeak_data_path),
            "-p", "1.0"
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(piper_dir) # Roda a partir da pasta do piper pra achar DLLs
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(input=text.encode('utf-8')), timeout=30.0)

            if process.returncode == 0 and out_wav.exists():
                return ExecutionResult(
                    plan_id=plan.id,
                    status=ExecutionStatus.SUCCESS,
                    output=f"Audio salvo em: {out_wav}",
                    started_at=datetime.now(_UTC),
                    finished_at=datetime.now(_UTC)
                )
            else:
                err = stderr.decode('utf-8', errors='replace').strip()
                return ExecutionResult(
                    plan_id=plan.id,
                    status=ExecutionStatus.FAILED,
                    errors=[f"Piper falhou: {err}"]
                )
        except Exception as e:
            return ExecutionResult(
                plan_id=plan.id,
                status=ExecutionStatus.FAILED,
                errors=[f"Erro inesperado no Piper: {str(e)}"]
            )