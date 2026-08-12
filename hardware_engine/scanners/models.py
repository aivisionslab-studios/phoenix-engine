"""
scanners/models.py
=====================
Descoberta de modelos em disco: GGUF, Safetensors, checkpoints .ckpt/.pt,
LoRAs, embeddings, VAE, ControlNet. A classificação "kind_guess" é uma
heurística baseada em nome de pasta/arquivo — é só um palpite para
facilitar a navegação no Manifest, nunca uma verdade absoluta (a
Telemetria não interpreta o conteúdo do modelo).

Hash: para não travar em arquivos de dezenas de GB, usamos um hash
"esparso" (tamanho + primeiros/últimos N bytes) por padrão. Hash
completo (sha256 do arquivo inteiro) é opcional via full_hash=True.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Iterable

EXTENSIONS = {
    ".gguf": "GGUF",
    ".safetensors": "Safetensors",
    ".ckpt": "Checkpoint",
    ".pt": "PyTorch",
    ".bin": "Bin/Diffusers",
    ".onnx": "ONNX",
}

KIND_HINTS = [
    ("lora", "LoRA"),
    ("embedding", "Embedding"),
    ("textual_inversion", "Embedding"),
    ("vae", "VAE"),
    ("controlnet", "ControlNet"),
    ("checkpoint", "Checkpoint"),
]


def _guess_kind(path: str) -> str:
    lowered = path.lower()
    for hint, kind in KIND_HINTS:
        if hint in lowered:
            return kind
    return "Checkpoint/Modelo base"


def _sparse_hash(path: str, chunk: int = 1_048_576) -> str:
    h = hashlib.sha256()
    size = os.path.getsize(path)
    h.update(str(size).encode())
    with open(path, "rb") as f:
        h.update(f.read(chunk))
        if size > chunk:
            f.seek(-min(chunk, size), os.SEEK_END)
            h.update(f.read(chunk))
    return h.hexdigest()


def _full_hash(path: str, chunk: int = 8 * 1_048_576) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def scan_models(search_dirs: Iterable[str], full_hash: bool = False,
                 max_files: int = 5000) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    count = 0
    for base in search_dirs:
        base_path = Path(os.path.expanduser(os.path.expandvars(base)))
        if not base_path.exists():
            continue
        for path in base_path.rglob("*"):
            if count >= max_files:
                break
            if not path.is_file():
                continue
            ext = path.suffix.lower()
            if ext not in EXTENSIONS:
                continue
            try:
                stat = path.stat()
                content_hash = _full_hash(str(path)) if full_hash else _sparse_hash(str(path))
                results.append({
                    "name": path.name,
                    "format": EXTENSIONS[ext],
                    "path": str(path),
                    "size_bytes": stat.st_size,
                    "modified_at": stat.st_mtime,
                    "content_hash": content_hash,
                    "kind_guess": _guess_kind(str(path)),
                })
                count += 1
            except (OSError, PermissionError):
                continue
    return results
