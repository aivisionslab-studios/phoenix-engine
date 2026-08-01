"""
ModelScanner — Varre Models/ e constrói inventário.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from datetime import datetime, timezone

try:
    from phoenix_kernel.paths import PhoenixPaths
except ImportError:
    PhoenixPaths = None

SUPPORTED = {
    ".gguf": "GGUF",
    ".safetensors": "Safetensors",
    ".onnx": "ONNX",
    ".mlx": "MLX",
    ".bin": "Bin",
    ".pt": "PyTorch",
    ".ckpt": "Checkpoint",
}


class ModelScanner:

    @staticmethod
    def scan_all(models_base: Path = None) -> list[dict]:
        if models_base is None:
            if PhoenixPaths:
                models_base = PhoenixPaths.get_models_base()
            else:
                models_base = Path("data/workstations/Models")
        if not models_base.exists():
            return []

        inventory = []
        for cat_dir in sorted(models_base.iterdir()):
            if not cat_dir.is_dir() or cat_dir.name.startswith("."):
                continue
            category = cat_dir.name
            for sub_dir in sorted(cat_dir.iterdir()):
                if not sub_dir.is_dir() or sub_dir.name.startswith("."):
                    continue
                subcategory = sub_dir.name
                for f in sub_dir.rglob("*"):
                    if f.is_file() and f.suffix.lower() in SUPPORTED:
                        inventory.append(ModelScanner._record(f, category, subcategory))
        return inventory

    @staticmethod
    def _record(f: Path, category: str, subcategory: str) -> dict:
        st = f.stat()
        return {
            "name": f.stem,
            "filename": f.name,
            "relative_path": str(f.relative_to(PhoenixPaths.get_models_base())) if PhoenixPaths else str(f),
            "category": category,
            "subcategory": subcategory,
            "format": SUPPORTED.get(f.suffix.lower(), "Unknown"),
            "size_bytes": st.st_size,
            "size_mb": round(st.st_size / (1024 * 1024), 2),
            "modified_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
            "sha256_prefix": ModelScanner._hash(f),
        }

    @staticmethod
    def _hash(f: Path) -> str:
        h = hashlib.sha256()
        try:
            with open(f, "rb") as fh:
                for _ in range(8):  # Apenas primeiros 64KB para velocidade
                    chunk = fh.read(8192)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()[:16]
        except OSError:
            return "unreadable"
