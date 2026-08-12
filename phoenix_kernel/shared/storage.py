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
        storage_candidates = []
        if os.name == "nt":
            programdata = os.environ.get("ProgramData")
            if programdata:
                storage_candidates.append(Path(programdata) / "Phoenix" / "storage.json")
        else:
            storage_candidates.append(Path("/etc/phoenix/storage.json"))
            
        storage_candidates.append(Path("data/storage.json"))
        
        for p in storage_candidates:
            if p.exists():
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        logger.info(f"StorageManager: Mapa de armazenamento carregado de {p}")
                        return data
                except Exception as e:
                    logger.error(f"StorageManager: Erro ao ler {p} - {e}")
                    
        logger.warning("StorageManager: storage.json não encontrado. Usando padrão local.")
        ws_fallback = str(Path("data/workstations").resolve())
        return {
            "workspace": ws_fallback,
            "models": str(Path(ws_fallback) / "Models"),
            "docker": "data/docker",
            "rag": "data/rag",
            "cache": "data/cache",
            "logs": "data/logs"
        }

    def get_workspace(self) -> str:
        return self.config.get("workspace", ".")
        
    def get_models_path(self) -> str:
        path = self.config.get("models", str(Path(self.get_workspace()) / "Models"))
        Path(path).mkdir(parents=True, exist_ok=True)
        return path
        
    def get_apps_path(self) -> str:
        path = os.path.join(self.config.get("workspace", "."), "apps")
        Path(path).mkdir(parents=True, exist_ok=True)
        return path

    def get_rag_path(self) -> str:
        path = self.config.get("rag", "data/rag")
        Path(path).mkdir(parents=True, exist_ok=True)
        return path

storage = StorageManager()