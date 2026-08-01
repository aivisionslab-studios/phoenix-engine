from __future__ import annotations
import asyncio
import logging
import platform
import unicodedata
from pathlib import Path
from datetime import datetime, timezone

from core.domain.execution import ExecutionPlan, ExecutionResult, ExecutionStatus
from core.domain.runtime import RuntimeStatus, RuntimeState
from phoenix_kernel.paths import PhoenixPaths

logger = logging.getLogger(__name__)
_UTC = timezone.utc


def _sanitize_prompt_for_cli(prompt: str) -> tuple[str, bool]:
    """
    PHX-FIX: o Windows converte a linha de comando (UTF-16 interno) para a
    codepage ANSI do sistema (normalmente Windows-1252 em pt-BR) ANTES de
    entregar pro argv de um binário C/C++ comum como o sd-cli.exe. O
    sd-cli então trata esses bytes como se fossem UTF-8 (o que o
    tokenizer do CLIP/T5 espera) - só que não são. Resultado: "dragão"
    chega corrompido, o encoder de texto não reconhece a palavra, e a
    imagem sai genérica, sem relação com o prompt.

    Isso NÃO depende do Python (que já lida com unicode direito) - é uma
    conversão que o próprio Windows faz na fronteira entre processos, fora
    do nosso controle. A correção robusta (funciona independente da
    codepage do sistema, sem precisar mexer em configuração regional do
    Windows) é remover os acentos ANTES de montar o comando: decompõe
    "ã" em "a" + acento (NFKD) e descarta o acento, sobrando só ASCII
    puro - que atravessa qualquer codepage sem erro.

    Só aplica no Windows. No Linux o subprocess já lida com UTF-8
    nativamente (locale do sistema é UTF-8 por padrão), então o prompt
    original com acentos passa reto, sem necessidade de sanitizar.

    Retorna (prompt_final, foi_alterado).
    """
    if platform.system() != "Windows":
        return prompt, False

    normalized = unicodedata.normalize("NFKD", prompt)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_only, ascii_only != prompt


def _discover_project_root(start_file: Path) -> Path:
    """
    NAO conta '.parent' no escuro. Sobe a arvore de diretorios a partir
    deste arquivo procurando uma pasta que contenha 'repos/stable-diffusion.cpp'.
    Se nao achar em nenhum nivel, cai de volta pro calculo antigo (4 parents,
    ou seja, a pasta que contem 'phoenix_kernel') e loga um AVISO explicito
    para que o erro apareca no log em vez de falhar silenciosamente.
    """
    current = start_file.resolve()
    for _ in range(8):  # sobe no maximo 8 niveis, nunca trava em loop infinito
        current = current.parent
        candidate = current / "repos" / "stable-diffusion.cpp"
        if candidate.exists():
            logger.info(f"SdCppDriver: raiz do projeto encontrada em '{current}' (achou '{candidate}')")
            return current
    # Fallback: assume que a raiz eh a pasta-mae de 'phoenix_kernel'
    fallback = start_file.resolve().parent.parent.parent.parent
    logger.warning(
        f"SdCppDriver: NAO achei 'repos/stable-diffusion.cpp' subindo a arvore a partir de "
        f"'{start_file}'. Usando fallback '{fallback}'. Se o sd-cli.exe nao for encontrado, "
        f"o problema NAO e contagem de .parent -- e que a pasta 'repos' nao existe onde este "
        f"processo Python acha que o projeto esta. Confira se este .py e o mesmo arquivo que a "
        f"API esta de fato executando (Get-Process python -> Path)."
    )
    return fallback


class SdCppDriver:
    def __init__(self, *args, **kwargs) -> None:
        self._project_root = _discover_project_root(Path(__file__))
        self._process = None
        self._port = 7860  # Porta oficial do SD Server

    @property
    def name(self) -> str:
        return "stable-diffusion.cpp"

    def _find_executable(self) -> str | None:
        repo_dir = self._project_root / "repos" / "stable-diffusion.cpp"
        exe_names = ["sd-cli.exe", "sd.exe"] if platform.system() == "Windows" else ["sd-cli", "sd"]
        tried: list[str] = []
        for name in exe_names:
            paths = [repo_dir / "build" / "bin" / "Release" / name, repo_dir / "build" / "bin" / name]
            for p in paths:
                tried.append(str(p))
                if p.exists():
                    return str(p)
        logger.error(
            f"SdCppDriver: sd-cli.exe NAO encontrado. project_root='{self._project_root}'. "
            f"Caminhos tentados: {tried}"
        )
        return None

    def _find_model_file(self, model_name: str) -> Path | None:
        clean = model_name.split(":")[0].replace("/", "-").lower()
        image_dir = PhoenixPaths.get_category_path("Image")
        if not image_dir.exists():
            return None
        matches = list(image_dir.rglob(f"*{clean}*.gguf"))
        return matches[0] if matches else None

    def _find_component(self, comp_name: str) -> Path | None:
        image_dir = PhoenixPaths.get_category_path("Image")
        if not image_dir.exists():
            return None
        matches = list(image_dir.rglob(f"*{comp_name}*"))
        return matches[0] if matches else None

    async def start(self, plan: ExecutionPlan | None = None) -> bool:
        exe = self._find_executable()
        if exe is None:
            # log ja foi emitido dentro de _find_executable com o motivo exato
            return False
        return True

    async def stop(self) -> bool:
        if self._process and self._process.returncode is None:
            self._process.terminate()
            await self._process.wait()
        self._process = None
        return True

    async def status(self) -> RuntimeStatus:
        state = RuntimeState.RUNNING if self._find_executable() else RuntimeState.STOPPED
        return RuntimeStatus(name=self.name, state=state)

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        exe_path = self._find_executable()
        if not exe_path:
            return ExecutionResult(
                plan_id=plan.id, status=ExecutionStatus.FAILED,
                errors=[
                    f"sd-cli.exe nao encontrado. project_root calculado: '{self._project_root}'. "
                    f"Verifique o log em nivel ERROR acima para ver os caminhos exatos tentados."
                ]
            )

        model_name = plan.model if plan.model else "flux"
        model_path = self._find_model_file(model_name)

        if not model_path:
            return ExecutionResult(
                plan_id=plan.id, status=ExecutionStatus.FAILED,
                errors=[f"Arquivo do modelo '{model_name}' nao encontrado no disco."]
            )

        output_dir = self._project_root / "output" / "images"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"phoenix_{datetime.now().strftime('%H%M%S')}.png"

        raw_prompt = plan.parameters.get("prompt", "a majestic phoenix bird, cinematic lighting, 8k")

        # PHX-FIX: ver docstring de _sanitize_prompt_for_cli. Evita o bug
        # de acentuação corrompida (Windows ANSI codepage -> argv) que
        # fazia o sd-cli ignorar palavras-chave em português como "dragão".
        prompt, prompt_changed = _sanitize_prompt_for_cli(raw_prompt)
        if prompt_changed:
            logger.warning(
                f"SdCppDriver: prompt continha acentos/caracteres não-ASCII e foi "
                f"normalizado pra evitar corrupção via codepage do Windows. "
                f"Original: \"{raw_prompt}\" -> Enviado: \"{prompt}\""
            )

        is_flux = "flux" in model_name.lower()

        # PHX-FIX: removida a flag "-ngl", "99". Ela NUNCA existiu no
        # sd-cli (é exclusiva do llama.cpp, onde controla quantas camadas
        # jogar na GPU). O stable-diffusion.cpp funciona ao contrário: ele
        # já roda 100% na GPU por padrão, porque o binário foi compilado
        # com o backend Vulkan/CUDA - só existem flags pra EMPURRAR partes
        # de volta pra CPU (--clip-on-cpu, --vae-on-cpu, --offload-to-cpu),
        # nunca pra "ligar" a GPU. Mandar "-ngl" só fazia o sd-cli.exe
        # recusar o comando inteiro com "unknown argument: -ngl" antes de
        # sequer tentar carregar o modelo.
        cmd = [
            exe_path,
            # FLUX usa --diffusion-model (arquitetura desacoplada), SD1.5/SDXL usa -m
            "--diffusion-model" if is_flux else "-m", str(model_path),
            "-p", prompt,
            "-o", str(output_file),
            "-H", "512", "-W", "512",
            "--steps", "4",
            "--seed", "42",
        ]

        if is_flux:
            vae_path = self._find_component("ae")
            clip_path = self._find_component("clip_l")
            t5_path = self._find_component("t5xxl")

            missing = [n for n, p in [("vae/ae.safetensors", vae_path), ("clip_l", clip_path), ("t5xxl", t5_path)] if p is None]
            if missing:
                return ExecutionResult(
                    plan_id=plan.id, status=ExecutionStatus.FAILED,
                    errors=[f"Componentes do FLUX ausentes no disco: {missing}. Baixe-os antes de gerar imagem."]
                )

            cmd.extend(["--vae", str(vae_path)])
            cmd.extend(["--clip_l", str(clip_path)])
            cmd.extend(["--t5xxl", str(t5_path)])
            cmd.extend([
                "--cfg-scale", "1.0",
                "--clip-on-cpu",
                "--vae-on-cpu",
                "--vae-tiling",
            ])

        logger.info(f"SdCppDriver: Executando comando Vulkan: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path(exe_path).parent)
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=900.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ExecutionResult(
                    plan_id=plan.id, status=ExecutionStatus.FAILED,
                    errors=["Timeout: A geracao da imagem demorou mais de 15 minutos e foi abortada."]
                )

            if output_file.exists():
                logger.info(f"SdCppDriver: Imagem gerada com sucesso em {output_file}")
                return ExecutionResult(
                    plan_id=plan.id,
                    status=ExecutionStatus.SUCCESS,
                    output=f"Imagem salva em: {output_file}",
                    started_at=datetime.now(_UTC),
                    finished_at=datetime.now(_UTC)
                )
            else:
                err_text = stderr.decode("utf-8", errors="replace").strip()
                logger.error(f"SdCppDriver: Falha ao gerar imagem. stderr: {err_text}")
                return ExecutionResult(
                    plan_id=plan.id, status=ExecutionStatus.FAILED,
                    errors=[f"Falha na geracao. stderr do sd-cli: {err_text[-500:]}"]
                )

        except Exception as exc:
            logger.error(f"SdCppDriver: Erro inesperado: {exc}")
            return ExecutionResult(
                plan_id=plan.id, status=ExecutionStatus.FAILED,
                errors=[f"Erro ao executar sd-cli: {str(exc)}"]
            )
