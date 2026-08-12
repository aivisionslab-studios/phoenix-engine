from __future__ import annotations
import asyncio
import logging
import platform
import unicodedata
import psutil
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
    codepage ANSI do sistema ANTES de entregar pro argv do sd-cli.exe.
    Remove acentos (NFKD) antes de montar o comando pra evitar prompt
    corrompido. Só aplica no Windows — no Linux o subprocess já lida com
    UTF-8 nativamente.
    """
    if platform.system() != "Windows":
        return prompt, False
    normalized = unicodedata.normalize("NFKD", prompt)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_only, ascii_only != prompt


def _discover_project_root(start_file: Path) -> Path:
    current = start_file.resolve()
    for _ in range(8):
        current = current.parent
        candidate = current / "repos" / "stable-diffusion.cpp"
        if candidate.exists():
            logger.info(f"SdCppDriver: raiz do projeto encontrada em '{current}'")
            return current
    fallback = start_file.resolve().parent.parent.parent.parent
    logger.warning(
        f"SdCppDriver: NAO achei 'repos/stable-diffusion.cpp' subindo a arvore a partir de "
        f"'{start_file}'. Usando fallback '{fallback}'."
    )
    return fallback


# ---------------------------------------------------------------------------
# PHX-FIX: Perfis por familia de modelo.
#
# Antes deste fix, o driver so sabia montar UM formato de comando (Flux
# generico com steps=4 fixo e cfg-scale=1.0 fixo), o que nao bate com os
# comandos validados manualmente pra Kontext, Flux Q8, Flux.2, Juggernaut
# XL (SDXL) e SD 3.5 Large. Cada familia tem encoders diferentes, flags de
# offload diferentes, cfg-scale diferente e resolucao padrao diferente -
# entao cada uma precisa do proprio perfil, na ordem certa de deteccao
# (mais especifico primeiro: "kontext" tem que casar antes de "flux1-dev"
# generico).
#
# "match": substrings (case-insensitive) procuradas no nome do arquivo do
#          modelo pra escolher o perfil.
# "diffusion_flag": True usa --diffusion-model (arquitetura Flux
#          desacoplada), False usa -m (checkpoint unico, SDXL/SD1.5/SD3.5).
# "components": lista de (nome_do_flag_cli, [substrings pra achar o arquivo]).
#          Todos sao obrigatorios - se faltar um, falha com erro claro.
# "extra_flags": flags fixas de offload/qualidade desse perfil.
# "cfg_scale": valor de --cfg-scale, ou None se o perfil nao usa a flag.
# "default_resolution": (largura, altura) usada se o plano nao especificar.
# ---------------------------------------------------------------------------
MODEL_PROFILES = [
    {
        "name": "flux-kontext",
        "match": ["kontext"],
        "diffusion_flag": True,
        "components": [
            ("--vae", ["ae.safetensors", "flux-vae"]),
            ("--clip_l", ["clip_l"]),
            ("--t5xxl", ["t5xxl"]),
        ],
        "extra_flags": ["--vae-on-cpu", "--clip-on-cpu", "--offload-to-cpu"],
        "cfg_scale": "1.0",
        "default_resolution": (512, 512),
        "default_steps": 4,
    },
    {
        # PHX-FIX: Flux1-schnell - modelo destilado (mesma familia do
        # Kontext), precisa casar ANTES do "flux1-dev" generico, senao
        # "flux1-schnell-q4_0.gguf" bate no padrao generico "flux1" do
        # perfil dev e cai faltando steps/cfg-scale corretos (schnell usa
        # 4 steps e cfg-scale 1.0, nao 20 steps / cfg 3.5 do dev).
        "name": "flux1-schnell",
        "match": ["schnell"],
        "diffusion_flag": True,
        "components": [
            ("--vae", ["ae.safetensors", "flux-vae"]),
            ("--clip_l", ["clip_l"]),
            ("--t5xxl", ["t5xxl"]),
        ],
        "extra_flags": ["--vae-on-cpu", "--clip-on-cpu", "--offload-to-cpu"],
        "cfg_scale": "1.0",
        "default_resolution": (512, 512),
        "default_steps": 4,
    },
    {
        "name": "flux2-dev",
        "match": ["flux2", "flux-2", "flux.2"],
        "diffusion_flag": True,
        "components": [
            ("--vae", ["ae.safetensors", "flux-vae"]),
            ("--clip_l", ["clip_l"]),
            ("--t5xxl", ["t5xxl"]),
        ],
        "extra_flags": ["--vae-on-cpu", "--clip-on-cpu", "--offload-to-cpu"],
        "cfg_scale": "3.5",
        "default_resolution": (512, 512),
        "default_steps": 20,
    },
    {
        # Flux1-dev generico (Q4/Q8/etc) - checado DEPOIS de kontext/flux2
        # pra nao roubar o match deles, ja que "flux1-dev" pode aparecer
        # em nomes de arquivo variados.
        "name": "flux1-dev",
        "match": ["flux1-dev", "flux1_dev", "flux-dev", "flux_dev"],
        "diffusion_flag": True,
        "components": [
            ("--vae", ["ae.safetensors", "flux-vae"]),
            ("--clip_l", ["clip_l"]),
            ("--t5xxl", ["t5xxl"]),
        ],
        "extra_flags": ["--vae-on-cpu", "--clip-on-cpu", "--offload-to-cpu"],
        "cfg_scale": "3.5",
        "default_resolution": (512, 512),
        "default_steps": 20,
    },
    {
        "name": "sd35-large",
        "match": ["sd3.5_large", "sd35_large", "sd3.5-large", "sd3_5_large"],
        "diffusion_flag": False,
        "components": [
            ("--clip_l", ["clip_l"]),
            ("--clip_g", ["clip_g"]),
            ("--t5xxl", ["t5xxl"]),
        ],
        "extra_flags": ["--vae-on-cpu", "--clip-on-cpu", "--offload-to-cpu"],
        "cfg_scale": None,
        "default_resolution": (512, 512),
        "default_steps": 20,
    },
    {
        "name": "sd35-medium",
        "match": ["sd3.5_medium", "sd35_medium", "sd3.5-medium", "sd3_5_medium"],
        "diffusion_flag": False,
        "components": [
            ("--clip_l", ["clip_l"]),
            ("--clip_g", ["clip_g"]),
            ("--t5xxl", ["t5xxl"]),
        ],
        "extra_flags": ["--vae-on-cpu", "--clip-on-cpu", "--offload-to-cpu"],
        "cfg_scale": None,
        "default_resolution": (512, 512),
        "default_steps": 20,
    },
    {
        # Juggernaut XL e outros fine-tunes SDXL: checkpoint unico + vae
        # separado (fix fp16), sem clip/t5xxl - so precisa do vae na CPU.
        "name": "sdxl-checkpoint",
        "match": ["juggernaut", "sdxl", "dreamshaper"],
        "diffusion_flag": False,
        "components": [
            ("--vae", ["sdxl_vae-fp16-fix", "sdxl-vae"]),
        ],
        "extra_flags": ["--vae-on-cpu"],
        "cfg_scale": None,
        "default_resolution": (1024, 1024),
        "default_steps": 20,
    },
]

# Perfil de fallback quando nenhum padrao acima casa - mantem o
# comportamento antigo (checkpoint simples, sem encoders extras) pra nao
# quebrar modelos SD1.5 e outros checkpoints "-m" puros.
DEFAULT_PROFILE = {
    "name": "generic-checkpoint",
    "match": [],
    "diffusion_flag": False,
    "components": [],
    "extra_flags": [],
    "cfg_scale": None,
    "default_resolution": (512, 512),
    "default_steps": 20,
}


def _select_profile(model_name: str) -> dict:
    lowered = model_name.lower()
    for profile in MODEL_PROFILES:
        if any(token in lowered for token in profile["match"]):
            return profile
    return DEFAULT_PROFILE


# ---------------------------------------------------------------------------
# PHX-FIX: Bloqueios rigidos - combinacoes CONFIRMADAS como falha nesta
# maquina (RX 580 8GB + Xeon E5, 32GB RAM), extraidas de um dia inteiro de
# benchmark manual documentado em transcript real. Cada uma foi tentada
# com as flags de offload/split disponiveis no sd-cli e falhou do mesmo
# jeito todas as vezes - nao e falta de flag, e limite fisico do hardware.
#
# Isso NAO e uma lista de "cuidado" - e uma lista de "nunca tentar de
# novo". A pior das cinco (SD 3.5 Large) nao deu OOM controlado: travou
# a maquina inteira (RAM saturada, tela preta, precisou resetar). Por
# isso o check roda ANTES de qualquer subprocess ser aberto, nao depois.
# ---------------------------------------------------------------------------
def _check_known_failure(profile: dict, model_path: Path, width: int, height: int) -> str | None:
    lowered = model_path.name.lower()
    try:
        size_gb = model_path.stat().st_size / (1024 ** 3)
    except OSError:
        size_gb = 0.0

    # SD 3.5 Large: nao trava com OOM controlado - trava a MAQUINA
    # INTEIRA (RAM saturada, tela preta, precisou hard reset). Bloqueio
    # total, independente de resolucao ou flags - nao existe combinacao
    # segura testada nesta maquina (8GB VRAM / 32GB RAM).
    if profile["name"] == "sd35-large":
        return (
            "SD 3.5 Large (checkpoint ~16.5GB) travou a maquina inteira num teste anterior "
            "nesta configuracao de hardware (RAM saturada, tela preta, sem log de OOM - "
            "precisou hard reset). Bloqueado preventivamente independente de resolucao/flags. "
            "Nao ha combinacao validada como segura ate hoje."
        )

    # Flux Q8: OOM confirmado mesmo em 512x512 com offload total - o
    # modelo sozinho (12.7GB) ja estoura o orcamento de VRAM+buffer da
    # RX 580, nao tem split que resolva.
    if profile["name"] in ("flux1-dev", "flux1-schnell", "flux-kontext", "flux2-dev") and "q8" in lowered:
        return (
            "Flux Q8 (~12.7GB) deu OOM mesmo em 512x512 com --offload-to-cpu completo "
            "(buffer de 1063888896 bytes nao alocado). Nao ha resolucao segura testada "
            "pra essa quantizacao nesta GPU de 8GB."
        )

    # Flux.2: o VAE do Flux.1 (ae.safetensors) NAO e compativel - shape
    # mismatch confirmado ([3,3,16,512] vs [3,3,32,512]). Nao e um
    # problema de VRAM, e o arquivo errado - bloqueia ate existir um VAE
    # especifico do Flux.2 catalogado.
    if profile["name"] == "flux2-dev":
        return (
            "Flux.2 dev deu erro de VAE incompativel usando o ae.safetensors do Flux.1 "
            "(shape esperado [3,3,32,512], recebido [3,3,16,512]). Precisa de um VAE "
            "especifico do Flux.2 - ainda nao catalogado nesta instalacao."
        )

    # Regra dos 6.3GB: modelo de difusao Flux acima de ~5.5GB (Q4 pra
    # cima) SEMPRE deu OOM de buffer de computacao em resolucao >512px,
    # testado com --offload-to-cpu, --backend clip=cpu,vae=cpu,... e
    # --max-vram - nenhum reduziu o buffer o suficiente. Só a
    # quantizacao Q3 (~5GB) coube em 768x768.
    if profile["name"] in ("flux1-dev", "flux1-schnell", "flux-kontext", "flux2-dev") and (width > 512 or height > 512):
        if size_gb > 5.5:
            return (
                f"Modelo de difusao Flux com {size_gb:.1f}GB em disco (acima do teto de ~5.5GB "
                f"pra caber em resolucao >512px nesta GPU). Testado com --offload-to-cpu, "
                f"--backend e --max-vram - todos deram OOM de compute buffer acima de 512x512 "
                f"pra modelos nessa faixa de tamanho. Só Q3 (~5GB) validado ate 768x768."
            )

    return None


class SdCppDriver:
    def __init__(self, *args, **kwargs) -> None:
        self._project_root = _discover_project_root(Path(__file__))
        self._process = None
        self._port = 7860

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
        logger.error(f"SdCppDriver: sd-cli.exe NAO encontrado. Caminhos tentados: {tried}")
        return None

    def _find_model_file(self, model_name: str) -> Path | None:
        clean = model_name.split(":")[0].replace("/", "-").lower()
        image_dir = PhoenixPaths.get_category_path("Image")
        candidates: list[Path] = []
        if image_dir.exists():
            candidates.extend(image_dir.rglob(f"*{clean}*.gguf"))
            candidates.extend(image_dir.rglob(f"*{clean}*.safetensors"))
        if candidates:
            return candidates[0]

        # PHX-FIX: fallback multi-disco, mesmo padrao ja usado no
        # LlamaCppDriver - modelos de imagem grandes as vezes vivem num
        # drive de backup separado (ex: "D:\BACKUP SSD NVME M2\models").
        logger.info(f"SdCppDriver: modelo '{model_name}' nao achado na pasta Image, varrendo discos...")
        for partition in psutil.disk_partitions(all=False):
            try:
                for root_hint in ["models", "image-models", Path("Phoenix") / "Workstations" / "Models" / "Image"]:
                    search_root = Path(partition.mountpoint) / root_hint
                    if not search_root.exists():
                        continue
                    matches = list(search_root.rglob(f"*{clean}*.gguf")) + list(search_root.rglob(f"*{clean}*.safetensors"))
                    if matches:
                        logger.info(f"SdCppDriver: modelo encontrado em {matches[0]}")
                        return matches[0]
            except PermissionError:
                continue
        return None

    def _find_component(self, hints: list[str]) -> Path | None:
        """
        Procura um arquivo de componente (vae/clip/t5xxl) por qualquer uma
        das substrings em 'hints', primeiro na pasta Image do Phoenix,
        depois varrendo pastas comuns em todos os discos - porque na
        maquina real esses arquivos ficam espalhados em subpastas
        diferentes (flux-vae/, flux-encoders/, sd35-encoders/text_encoders/,
        e ate em drives de backup fora da estrutura padrao do Phoenix).
        """
        image_dir = PhoenixPaths.get_category_path("Image")
        search_roots = [image_dir] if image_dir.exists() else []

        for partition in psutil.disk_partitions(all=False):
            try:
                for root_hint in ["models", "image-models"]:
                    candidate_root = Path(partition.mountpoint) / root_hint
                    if candidate_root.exists():
                        search_roots.append(candidate_root)
                backup_hint = Path(partition.mountpoint) / "models"
                if backup_hint.exists():
                    search_roots.append(backup_hint)
            except PermissionError:
                continue

        for root in search_roots:
            for hint in hints:
                matches = list(root.rglob(f"*{hint}*"))
                matches = [m for m in matches if m.suffix in (".safetensors", ".gguf", ".bin")]
                if matches:
                    return matches[0]
        return None

    async def start(self, plan: ExecutionPlan | None = None) -> bool:
        return self._find_executable() is not None

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
                errors=[f"sd-cli.exe nao encontrado. project_root: '{self._project_root}'."]
            )

        model_name = plan.model if plan.model else "flux"
        model_path = self._find_model_file(model_name)
        if not model_path:
            return ExecutionResult(
                plan_id=plan.id, status=ExecutionStatus.FAILED,
                errors=[f"Arquivo do modelo '{model_name}' nao encontrado no disco."]
            )

        profile = _select_profile(model_path.name)
        logger.info(f"SdCppDriver: modelo '{model_path.name}' -> perfil '{profile['name']}'")

        default_w, default_h = profile["default_resolution"]
        width = int(plan.parameters.get("width", default_w))
        height = int(plan.parameters.get("height", default_h))

        # PHX-FIX: bloqueio preventivo pra combinacoes JA confirmadas como
        # falha nesta maquina (ver _check_known_failure). Roda ANTES de
        # abrir qualquer subprocess - a pior falha documentada (SD 3.5
        # Large) nao foi um OOM controlado, foi a maquina inteira travando
        # com RAM saturada. Nao vale a pena nem tentar de novo.
        hazard = _check_known_failure(profile, model_path, width, height)
        if hazard:
            logger.error(f"SdCppDriver: bloqueado preventivamente - {hazard}")
            return ExecutionResult(
                plan_id=plan.id, status=ExecutionStatus.FAILED,
                errors=[f"Combinacao bloqueada (falha conhecida documentada): {hazard}"]
            )

        output_dir = self._project_root / "output" / "images"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"phoenix_{datetime.now().strftime('%H%M%S')}.png"

        raw_prompt = plan.parameters.get("prompt", "a majestic phoenix bird, cinematic lighting, 8k")
        prompt, prompt_changed = _sanitize_prompt_for_cli(raw_prompt)
        if prompt_changed:
            logger.warning(f"SdCppDriver: prompt normalizado (acentos removidos): \"{raw_prompt}\" -> \"{prompt}\"")

        # PHX-FIX: steps e resolucao agora vem do plano com fallback pro
        # default do perfil - antes eram 4 steps e 512x512 fixos pra
        # QUALQUER modelo, o que gerava imagens borradas no Flux (que
        # precisa de 20+ steps pra resolver detalhe) e cortava o Juggernaut/
        # SDXL, que espera 1024x1024.
        width, height = str(width), str(height)
        steps = str(plan.parameters.get("steps", profile.get("default_steps", 20)))
        seed = str(plan.parameters.get("seed", 42))

        cmd = [
            exe_path,
            "--diffusion-model" if profile["diffusion_flag"] else "-m", str(model_path),
            "-p", prompt,
            "-o", str(output_file),
            "-W", width, "-H", height,
            "--steps", steps,
            "--seed", seed,
        ]

        missing_components = []
        for flag, hints in profile["components"]:
            comp_path = self._find_component(hints)
            if comp_path is None:
                missing_components.append(f"{flag} ({'/'.join(hints)})")
            else:
                cmd.extend([flag, str(comp_path)])

        if missing_components:
            return ExecutionResult(
                plan_id=plan.id, status=ExecutionStatus.FAILED,
                errors=[
                    f"Perfil '{profile['name']}' requer componentes ausentes no disco: "
                    f"{', '.join(missing_components)}. Baixe-os antes de gerar imagem."
                ]
            )

        if profile["cfg_scale"] is not None:
            cmd.extend(["--cfg-scale", str(plan.parameters.get("cfg_scale", profile["cfg_scale"]))])

        cmd.extend(profile["extra_flags"])

        logger.info(f"SdCppDriver: Executando ({profile['name']}): {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path(exe_path).parent)
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=2700.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ExecutionResult(
                    plan_id=plan.id, status=ExecutionStatus.FAILED,
                    errors=["Timeout: geracao passou de 45 min (Flux com 50 steps pode chegar perto disso) e foi abortada."]
                )

            if output_file.exists():
                logger.info(f"SdCppDriver: Imagem gerada com sucesso em {output_file}")
                return ExecutionResult(
                    plan_id=plan.id, status=ExecutionStatus.SUCCESS,
                    output=f"Imagem salva em: {output_file} (perfil: {profile['name']})",
                    started_at=datetime.now(_UTC), finished_at=datetime.now(_UTC)
                )
            else:
                err_text = stderr.decode("utf-8", errors="replace").strip()
                logger.error(f"SdCppDriver: Falha ao gerar imagem. stderr: {err_text}")
                return ExecutionResult(
                    plan_id=plan.id, status=ExecutionStatus.FAILED,
                    errors=[f"Falha na geracao ({profile['name']}). stderr: {err_text[-500:]}"]
                )
        except Exception as exc:
            logger.error(f"SdCppDriver: Erro inesperado: {exc}")
            return ExecutionResult(
                plan_id=plan.id, status=ExecutionStatus.FAILED,
                errors=[f"Erro ao executar sd-cli: {str(exc)}"]
            )