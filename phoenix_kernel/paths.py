r"""
PhoenixPaths — Resolução dinâmica de caminhos.
Nenhum código Python deve conter C:\, D:\, E:\ ou /opt.
Tudo passa por aqui.
"""
from __future__ import annotations
import json
import os
import platform
from pathlib import Path


class PhoenixPaths:
    _manifest = None

    @classmethod
    def _load_manifest(cls) -> dict:
        if cls._manifest is not None:
            return cls._manifest
            
        storage_candidates = []
        if platform.system() == "Windows":
            programdata = os.environ.get("ProgramData")
            if programdata:
                storage_candidates.append(Path(programdata) / "Phoenix" / "storage.json")
        else:
            storage_candidates.append(Path("/etc/phoenix/storage.json"))
            
        # Fallback local na raiz do projeto
        storage_candidates.append(Path("data/storage.json"))
        
        for p in storage_candidates:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        cls._manifest = json.load(f)
                        return cls._manifest
                except Exception:
                    pass
                    
        cls._manifest = {"workspace": str(Path("data/workstations").resolve())}
        return cls._manifest

    @classmethod
    def get_workspace(cls) -> Path:
        ws = Path(cls._load_manifest().get("workspace", "."))
        if ws.is_absolute():
            ws.mkdir(parents=True, exist_ok=True)
            return ws
        # Fallback seguro
        fallback = Path("data/workstations").resolve()
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    @classmethod
    def get_models_base(cls) -> Path:
        return cls.get_workspace() / "Models"

    @classmethod
    def get_category_path(cls, category: str, subcategory: str = None) -> Path:
        base = cls.get_models_base() / category
        return base / subcategory if subcategory else base

    @classmethod
    def get_model_path(cls, category: str, subcategory: str, filename: str) -> Path:
        return cls.get_category_path(category, subcategory) / filename

    @classmethod
    def get_cache_dir(cls) -> Path:
        return cls.get_workspace().parent / "Cache"

    @classmethod
    def get_temp_dir(cls) -> Path:
        return cls.get_workspace().parent / "Temp"

    @classmethod
    def get_downloads_dir(cls) -> Path:
        return cls.get_workspace().parent / "Downloads"

    @classmethod
    def get_outputs_dir(cls) -> Path:
        return cls.get_workspace().parent / "Outputs"

    @classmethod
    def get_inventory_db(cls) -> Path:
        return cls.get_workspace().parent / "data" / "models_inventory.json"


# --- CONSTANTES DE SISTEMA E CLOUD SYNC ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = DATA_DIR / "config"

FIRESTORE_CREDENTIALS = CONFIG_DIR / "firestore_credentials.json"
MACHINE_ID_FILE = DATA_DIR / "machine_id.json"
CONSENT_FLAG = DATA_DIR / "telemetry_consent.flag"
KNOWLEDGE_BASE_JSON = DATA_DIR / "knowledge_base.json"

# PHX-NEW: pasta onde install_phoenix.ps1/common.ps1 já escrevem os
# relatórios de instalação (install_TIMESTAMP.log/.json) - cloud_sync.py
# passa a ler daqui pra sincronizar automaticamente, em vez desses logs
# ficarem só locais sem nunca virar conhecimento compartilhado.
INSTALL_LOGS_DIR = PROJECT_ROOT / "logs" / "install"

# PHX-NEW: cursor local do último pull do shared_knowledge_pool - guarda
# só um timestamp, pra pull_shared_knowledge_base() não rebaixar o pool
# inteiro toda vez, só o que mudou desde a última sincronização.
SHARED_POOL_CURSOR_FILE = DATA_DIR / "shared_pool_last_pull.json"
