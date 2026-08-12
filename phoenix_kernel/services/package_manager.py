import json
import logging
import asyncio
from pathlib import Path
from .provisioning import ProvisioningManager
from .catalog import CatalogEngine

logger = logging.getLogger(__name__)

class PackageManager:
    def __init__(self, budget_engine=None):
        self.catalog_path = Path("catalog/packages")
        self.categories = ["essentials", "studios", "suites", "addons"]
        self.catalog = CatalogEngine()
        self.provisioning = ProvisioningManager()
        self.budget = budget_engine

    def _find_package(self, package_name: str) -> Path | None:
        for category in self.categories:
            pkg_file = self.catalog_path / category / f"{package_name}.json"
            if pkg_file.exists(): return pkg_file
        return None

    def list_packages(self) -> str:
        output_lines = []
        for category in self.categories:
            cat_path = self.catalog_path / category
            if not cat_path.exists(): continue
            files = list(cat_path.glob("*.json"))
            if not files: continue
            output_lines.append(f"\n=== {category.upper()} ===")
            for f in files:
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        pkg = json.load(file)
                    output_lines.append(f"- {pkg.get('id', f.stem)}: {pkg.get('name', 'Sem nome')}")
                except: pass
        return "\n".join(output_lines) if output_lines else "Nenhum pacote encontrado."

    async def install_package(self, package_name: str) -> str:
        pkg_file = self._find_package(package_name)
        if not pkg_file: return f"[ERRO] Missão '{package_name}' não encontrada."

        with open(pkg_file, 'r', encoding='utf-8') as f:
            pkg = json.load(f)

        logger.info(f"PackageManager: Iniciando missão '{pkg.get('name')}'...")
        results = []
        connectors = pkg.get("connectors", [])
        loop = asyncio.get_running_loop()

        for conn_name in connectors:
            logger.info(f"PackageManager: Provisionando conector '{conn_name}'...")
            # RODA EM THREAD SEPARADA PARA NÃO TRAVAR A TELA
            result = await loop.run_in_executor(None, self.provisioning.install, conn_name)
            results.append(f"- {conn_name}: {result}")

        return f"Missão '{pkg.get('name')}' concluída!\n" + "\n".join(results)