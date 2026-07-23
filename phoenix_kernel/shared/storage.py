import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class StorageManager:
    """Lê o storage.json gerado pelo Bootstrapper. A Phoenix nunca descobre discos."""
    def __init__(self):
        self.config = self._load_config()
        
    def _load_config(self) -> dict:
        # Caminhos padrão onde o install_phoenix.ps1 salva o arquivo
        paths = [
            Path(os.environ.get("ProgramData", "C:\ProgramData")) / "Phoenix" / "storage.json",
            Path("/etc/phoenix/storage.json"),
            Path(".config/phoenix/storage.json") # Fallback relativo
        ]
        
        for p in paths:
            if p.exists():
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        logger.info(f"StorageManager: Mapa de armazenamento carregado de {p}")
                        return data
                except Exception as e:
                    logger.error(f"StorageManager: Erro ao ler {p} - {e}")
                    
        logger.warning("StorageManager: storage.json não encontrado. Usando padrão local (./data).")
        # Fallback seguro se o script PowerShell não tiver rodado
        return {
            "workspace": str(Path(".").resolve()),
            "models": "data/models",
            "docker": "data/docker",
            "rag": "data/rag",
            "cache": "data/cache",
            "logs": "data/logs"
        }

    def get_workspace(self) -> str:
        return self.config.get("workspace", ".")
        
    def get_models_path(self) -> str:
        path = self.config.get("models", "data/models")
        Path(path).mkdir(parents=True, exist_ok=True)
        return path
        
    def get_apps_path(self) -> str:
        # Compatibilidade com o InstallTargetSelector antigo
        path = os.path.join(self.config.get("workspace", "."), "apps")
        Path(path).mkdir(parents=True, exist_ok=True)
        return path

    def get_rag_path(self) -> str:
        path = self.config.get("rag", "data/rag")
        Path(path).mkdir(parents=True, exist_ok=True)
        return path

# Singleton para acesso global
storage = StorageManager()
