import logging
from .catalog import CatalogEngine

logger = logging.getLogger(__name__)

class PackageManager:
    def __init__(self):
        self.catalog = CatalogEngine()

    def list_packages(self) -> str:
        return self.catalog.list_packages()

    def resolve_mission(self, package_name: str) -> tuple[str, list[str]] | None:
        """Abre o JSON da missão e retorna apenas a lista de conectores."""
        pkg = self.catalog.get_package(package_name)
        if not pkg: return None
        return pkg.get("name", package_name), pkg.get("connectors", [])
