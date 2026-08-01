r"""
PhoenixPaths — Resolução dinâmica de caminhos.
Nenhum código Python deve conter C:\, D:\, E:\ ou /opt.
Tudo passa por aqui.
"""
from __future__ import annotations
import json
import platform
from pathlib import Path


class PhoenixPaths:
    _manifest = None

    @classmethod
    def _load_manifest(cls) -> dict:
        if cls._manifest is not None:
            return cls._manifest
        if platform.system() == "Windows":
            p = Path("C:/ProgramData/Phoenix/storage.json")
        else:
            p = Path("/etc/phoenix/storage.json")
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                cls._manifest = json.load(f)
        else:
            cls._manifest = {"workspace": str(Path("data/workstations").resolve())}
        return cls._manifest

    @classmethod
    def get_workspace(cls) -> Path:
        ws = Path(cls._load_manifest().get("workspace", "."))
        return ws if ws.is_absolute() else Path("data/workstations").resolve()

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
# Estas constantes referenciam o diretório base do projeto dinamicamente,
# garantindo que funcione em qualquer unidade (C:, D:, E:, /opt, etc.)

# Raiz do projeto (onde está o api_server.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Diretório de dados locais da Phoenix (config, flags, credenciais)
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = DATA_DIR / "config"

# Arquivos específicos utilizados pelo cloud_sync.py
FIRESTORE_CREDENTIALS = CONFIG_DIR / "firestore_credentials.json"
MACHINE_ID_FILE = DATA_DIR / "machine_id.json"
CONSENT_FLAG = DATA_DIR / "telemetry_consent.flag"

# Arquivo de base de conhecimento sincronizado do Firestore
KNOWLEDGE_BASE_JSON = DATA_DIR / "knowledge_base.json"