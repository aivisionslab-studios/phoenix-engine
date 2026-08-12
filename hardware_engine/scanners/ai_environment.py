"""
scanners/ai_environment.py
=============================
Detecção de ferramentas de IA instaladas. Extensível: novas ferramentas
podem ser adicionadas via `register_connector()` sem alterar este arquivo
(por exemplo, um conector separado carregado por um plugin da Phoenix).

Cada conector é uma função `() -> Optional[dict]` que retorna informações
se a ferramenta for encontrada, ou None caso contrário. A checagem é
sempre best-effort: comando no PATH, porta HTTP local respondendo, ou
diretório de instalação comum.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Optional

from ._utils import run_cmd, command_exists, safe

Connector = Callable[[], Optional[dict[str, Any]]]

_CONNECTORS: dict[str, Connector] = {}


def register_connector(name: str, fn: Connector) -> None:
    """Permite que módulos externos (conectores) adicionem novas ferramentas
    de IA à detecção sem tocar neste arquivo."""
    _CONNECTORS[name] = fn


def _via_command(cmd: str, version_args: list[str] | None = None) -> Optional[dict[str, Any]]:
    if not command_exists(cmd):
        return None
    version = None
    if version_args:
        version = run_cmd([cmd, *version_args])
    return {"detected": True, "method": "command", "path": cmd, "version": version}


def _via_paths(paths: list[str]) -> Optional[dict[str, Any]]:
    for p in paths:
        expanded = os.path.expanduser(os.path.expandvars(p))
        if os.path.exists(expanded):
            return {"detected": True, "method": "path", "path": expanded, "version": None}
    return None


def _detect_ollama() -> Optional[dict[str, Any]]:
    return _via_command("ollama", ["--version"])


def _detect_llama_cpp() -> Optional[dict[str, Any]]:
    for binname in ("llama-cli", "llama-server", "main"):
        found = _via_command(binname)
        if found:
            found["path"] = binname
            return found
    return _via_paths(["~/llama.cpp", "./llama.cpp", "C:\\llama.cpp"])


def _detect_koboldcpp() -> Optional[dict[str, Any]]:
    return _via_command("koboldcpp") or _via_paths(["~/koboldcpp", "./koboldcpp*"])


def _detect_lm_studio() -> Optional[dict[str, Any]]:
    return _via_paths([
        "~/.cache/lm-studio",
        "~/AppData/Local/LM-Studio",
        "/Applications/LM Studio.app",
    ])


def _detect_localai() -> Optional[dict[str, Any]]:
    return _via_command("local-ai")


def _detect_open_webui() -> Optional[dict[str, Any]]:
    return _via_command("open-webui")


def _detect_comfyui() -> Optional[dict[str, Any]]:
    return _via_paths(["~/ComfyUI", "./ComfyUI", "C:\\ComfyUI"])


def _detect_stable_diffusion_webui() -> Optional[dict[str, Any]]:
    return _via_paths(["~/stable-diffusion-webui", "./stable-diffusion-webui"])


def _detect_sd_cpp() -> Optional[dict[str, Any]]:
    return _via_command("sd") or _via_paths(["~/stable-diffusion.cpp", "./sd-server*"])


def _detect_whisper() -> Optional[dict[str, Any]]:
    return _via_command("whisper")


def _detect_whisper_cpp() -> Optional[dict[str, Any]]:
    return _via_command("whisper-cli") or _via_paths(["~/whisper.cpp", "./whisper.cpp"])


def _detect_anythingllm() -> Optional[dict[str, Any]]:
    return _via_paths(["~/AnythingLLM", "/Applications/AnythingLLM.app"])


def _detect_open_interpreter() -> Optional[dict[str, Any]]:
    return _via_command("interpreter")


def _detect_continue_dev() -> Optional[dict[str, Any]]:
    return _via_paths(["~/.continue"])


def _detect_vscode_ai_extensions() -> Optional[dict[str, Any]]:
    ext_dir = os.path.expanduser("~/.vscode/extensions")
    if not os.path.isdir(ext_dir):
        return None
    ai_markers = ("continue", "copilot", "codeium", "cody", "tabnine")
    found = [d for d in safe(lambda: os.listdir(ext_dir), []) or []
             if any(m in d.lower() for m in ai_markers)]
    if not found:
        return None
    return {"detected": True, "method": "path", "path": ext_dir, "version": None,
            "extensions_found": found}


_BUILTIN_CONNECTORS: dict[str, Connector] = {
    "ollama": _detect_ollama,
    "llama.cpp": _detect_llama_cpp,
    "koboldcpp": _detect_koboldcpp,
    "lm_studio": _detect_lm_studio,
    "localai": _detect_localai,
    "open_webui": _detect_open_webui,
    "comfyui": _detect_comfyui,
    "stable_diffusion_webui": _detect_stable_diffusion_webui,
    "stable_diffusion_cpp": _detect_sd_cpp,
    "whisper": _detect_whisper,
    "whisper_cpp": _detect_whisper_cpp,
    "anythingllm": _detect_anythingllm,
    "open_interpreter": _detect_open_interpreter,
    "continue_dev": _detect_continue_dev,
    "vscode_ai_extensions": _detect_vscode_ai_extensions,
}


def scan_ai_environment() -> list[dict[str, Any]]:
    """Roda todos os conectores (built-in + registrados externamente) e
    retorna apenas as ferramentas detectadas."""
    results = []
    all_connectors = {**_BUILTIN_CONNECTORS, **_CONNECTORS}
    for name, fn in all_connectors.items():
        found = safe(fn)
        if found:
            found["name"] = name
            results.append(found)
    return results
