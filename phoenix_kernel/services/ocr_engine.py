# phoenix_kernel/services/ocr_engine.py
import asyncio
import logging
import os
import platform
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

class OCREngine:
    def __init__(self):
        self._tesseract_path = self._find_tesseract()
        if not self._tesseract_path:
            logger.warning("OCREngine: Tesseract não encontrado. Instale com 'sudo apt install tesseract-ocr' (Linux) ou 'winget install tesseract' (Windows).")
        else:
            logger.info(f"OCREngine: Tesseract encontrado em {self._tesseract_path}")

    def _find_tesseract(self) -> str | None:
        """Encontra o executável do Tesseract no PATH ou em caminhos padrão do Windows."""
        # 1. Tenta achar no PATH do sistema (mais comum no Linux e installs corretos no Windows)
        tesseract_cmd = shutil.which("tesseract")
        if tesseract_cmd:
            return tesseract_cmd
        
        # 2. PHX-FIX: Fallback para caminhos fixos no Windows (ignora o PATH do terminal)
        # Isso resolve o erro onde o Python não vê o Tesseract mesmo após o instalador o ter colocado lá.
        if platform.system() == "Windows":
            common_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path
                    
        return None

    async def extract_text(self, image_path: str) -> str:
        """Extrai texto de uma imagem usando o binário tesseract nativo."""
        if not self._tesseract_path:
            return "[Erro: Tesseract não instalado no servidor]"

        if not Path(image_path).exists():
            return "[Erro: Arquivo de imagem não encontrado]"

        try:
            # O tesseract escreve o resultado no stdout se usarmos 'stdout' como segundo argumento
            process = await asyncio.create_subprocess_exec(
                self._tesseract_path, str(image_path), "stdout",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)

            if process.returncode == 0:
                text = stdout.decode('utf-8', errors='replace').strip()
                logger.info(f"OCR concluído para {image_path}. Texto extraído: {len(text)} caracteres.")
                return text
            else:
                err = stderr.decode('utf-8', errors='replace').strip()
                logger.error(f"OCREngine: Falha no Tesseract - {err}")
                return f"[Erro no OCR: {err}]"

        except asyncio.TimeoutError:
            logger.error("OCREngine: Timeout ao processar imagem.")
            return "[Erro: Timeout no OCR]"
        except Exception as e:
            logger.error(f"OCREngine: Erro inesperado - {e}")
            return f"[Erro no OCR: {str(e)}]"