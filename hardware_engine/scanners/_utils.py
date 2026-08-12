"""
_utils.py
=========
Helpers compartilhados pelos scanners. Nenhum scanner pode lançar exceção
para fora — falha de leitura vira "não detectado", nunca crash da
Telemetria. Isso é deliberado: a Telemetria é sistema nervoso sensorial,
não pode parar de funcionar por causa de uma ferramenta ausente.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Optional


def run_cmd(args: list[str], timeout: float = 4.0) -> Optional[str]:
    """Executa um comando externo com timeout curto. Retorna stdout ou None."""
    if shutil.which(args[0]) is None:
        return None
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def safe(fn, default=None):
    """Executa fn() suprimindo qualquer exceção. Usado em todo scanner opcional."""
    try:
        return fn()
    except Exception:
        return default
