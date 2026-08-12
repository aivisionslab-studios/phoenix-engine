# phoenix_kernel/runtime/drivers/mtmd_driver.py
#
# Driver de VISAO NATIVA da Phoenix.
# Usa o llama-mtmd-cli (ja incluso no llama.cpp compilado com Vulkan) -
# nenhum fork/compilacao extra e necessaria. Mesmo padrao de design do
# sd_cpp.py: CLI de um tiro (roda, processa, sai), acha binario e modelo
# sozinho, timeout defensivo.
#
# Gerado automaticamente por setup_vision.py em 2026-08-03T19:03:48

from __future__ import annotations

import asyncio
import logging
import platform
import psutil
from pathlib import Path
from datetime import datetime, timezone

from core.domain.execution import ExecutionPlan, ExecutionResult, ExecutionStatus
from core.domain.runtime import RuntimeStatus, RuntimeState
from phoenix_kernel.paths import PhoenixPaths

logger = logging.getLogger(__name__)
_UTC = timezone.utc


class MtmdDriver:
    """
    Driver para o llama-mtmd-cli (Visao).
    Usa o mesmo binario compilado do llama.cpp (build com GGML_VULKAN=ON),
    mas em modo CLI pontual - nao mantem um servidor HTTP em background.
    """

    def __init__(self, *args, **kwargs) -> None:
        # drivers/ -> runtime/ -> phoenix_kernel/ -> raiz do projeto
        self._project_root = Path(__file__).resolve().parent.parent.parent.parent

    @property
    def name(self) -> str:
        return "mtmd"

    # -----------------------------------------------------------------
    # Descoberta de binario e arquivos de modelo
    # -----------------------------------------------------------------
    def _find_executable(self) -> str | None:
        repo_dir = self._project_root / "repos" / "llama.cpp"
        exe_names = (
            ["llama-mtmd-cli.exe", "llama-mtmd-cli"]
            if platform.system() == "Windows"
            else ["llama-mtmd-cli"]
        )
        for name in exe_names:
            candidates = [
                repo_dir / "build" / "bin" / "Release" / name,
                repo_dir / "build" / "bin" / name,
            ]
            for c in candidates:
                if c.exists():
                    return str(c)
        return None

    def _find_model_file(self, model_name: str) -> Path | None:
        clean = model_name.split(":")[0].replace("/", "-").lower().replace("-", "").replace("_", "")
        chat_dir = PhoenixPaths.get_category_path("Chat", "GGUF")
        if not chat_dir.exists():
            return None
        for match in chat_dir.glob("*.gguf"):
            stem_norm = match.stem.lower().replace("-", "").replace("_", "")
            if clean not in stem_norm:
                continue
            if match.stat().st_size > 50 * 1024 * 1024 and "mmproj" not in match.name.lower():
                return match
        return None

    def _find_mmproj_file(self) -> Path | None:
        chat_dir = PhoenixPaths.get_category_path("Chat", "GGUF")
        if not chat_dir.exists():
            return None
        matches = list(chat_dir.glob("*mmproj*.gguf"))
        return matches[0] if matches else None

    # -----------------------------------------------------------------
    # Ciclo de vida (o runtime "vision" nao mantem processo persistente,
    # entao start/stop/status so reportam disponibilidade do binario)
    # -----------------------------------------------------------------
    async def start(self, plan: ExecutionPlan | None = None) -> bool:
        return self._find_executable() is not None

    async def stop(self) -> bool:
        return True

    async def status(self) -> RuntimeStatus:
        state = RuntimeState.RUNNING if self._find_executable() else RuntimeState.STOPPED
        return RuntimeStatus(name=self.name, state=state)

    # -----------------------------------------------------------------
    # Execucao real: roda o llama-mtmd-cli sobre uma imagem
    # -----------------------------------------------------------------
    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        exe_path = self._find_executable()
        if not exe_path:
            return ExecutionResult(
                plan_id=plan.id,
                status=ExecutionStatus.FAILED,
                errors=["llama-mtmd-cli nao encontrado. Compile o llama.cpp com Vulkan (GGML_VULKAN=ON)."],
            )

        model_name = plan.model if plan.model else "minicpmv"
        model_path = self._find_model_file(model_name)
        mmproj_path = self._find_mmproj_file()

        if not model_path or not mmproj_path:
            missing = []
            if not model_path:
                missing.append(f"modelo '{model_name}'")
            if not mmproj_path:
                missing.append("mmproj-model-f16.gguf")
            return ExecutionResult(
                plan_id=plan.id,
                status=ExecutionStatus.FAILED,
                errors=[f"Arquivos de visao ausentes no disco: {', '.join(missing)}"],
            )

        image_path = plan.parameters.get("image_path")
        prompt = plan.parameters.get("prompt", "Descreva esta imagem em detalhes.")

        if not image_path or not Path(image_path).exists():
            return ExecutionResult(
                plan_id=plan.id,
                status=ExecutionStatus.FAILED,
                errors=[f"Imagem nao encontrada em: {image_path}"],
            )

        # PHX-FIX: Adicionado -t (threads) para usar todos os núcleos da CPU e -n 256 para limitar o tamanho da resposta.
        cores = psutil.cpu_count(logical=True) or 8

        cmd = [
            exe_path,
            "-m", str(model_path),
            "--mmproj", str(mmproj_path),
            "--image", str(image_path),
            "-p", prompt,
            "-ngl", "0",  # CPU - deixa a GPU livre pro sd-server (mesma logica do qwen3:8b)
            "-c", "4096",
            "-t", str(cores),  # Usa todos os núcleos disponíveis
            "-n", "256",       # Limita a resposta a 256 tokens (acelera muito)
        ]

        logger.info("MtmdDriver: executando analise de imagem: %s", " ".join(cmd))

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path(exe_path).parent),
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ExecutionResult(
                    plan_id=plan.id,
                    status=ExecutionStatus.FAILED,
                    errors=["Timeout: a analise da imagem demorou mais de 3 minutos."],
                )

            output_text = stdout.decode("utf-8", errors="replace").strip()

            if "ASSISTANT:" in output_text:
                output_text = output_text.split("ASSISTANT:")[-1].strip()

            if output_text:
                logger.info("MtmdDriver: imagem analisada com sucesso.")
                return ExecutionResult(
                    plan_id=plan.id,
                    status=ExecutionStatus.SUCCESS,
                    output=output_text,
                    started_at=datetime.now(_UTC),
                    finished_at=datetime.now(_UTC),
                )

            err_text = stderr.decode("utf-8", errors="replace").strip()
            logger.error("MtmdDriver: saida vazia. stderr: %s", err_text)
            return ExecutionResult(
                plan_id=plan.id,
                status=ExecutionStatus.FAILED,
                errors=[f"Saida vazia do mtmd-cli. stderr: {err_text[-500:]}"],
            )

        except Exception as exc:
            logger.exception("MtmdDriver: erro inesperado")
            return ExecutionResult(
                plan_id=plan.id,
                status=ExecutionStatus.FAILED,
                errors=[f"Erro ao executar mtmd-cli: {exc}"],
            )