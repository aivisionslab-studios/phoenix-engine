import logging
from .catalog import CatalogEngine
from .install_target import InstallTargetSelector
# CORREÇÃO: Importando da nova pasta estrutural install/connectors/
from ..install.connectors.connectors import WingetConnector, DockerConnector, GitConnector

logger = logging.getLogger(__name__)

class ProvisioningEngine:
    def __init__(self, event_bus=None):
        self.catalog = CatalogEngine()
        self.target = InstallTargetSelector()
        self.winget = WingetConnector()
        self.docker = DockerConnector()
        self.git = GitConnector()
        self.event_bus = event_bus # Injeta o EventBus, NÃO o Logs

    def _check_dependency(self, provider: str) -> bool:
        if provider == "docker":
            return self.docker._is_docker_running()
        return True

    def execute(self, pkg_name: str, connectors: list[str]) -> str:
        results = []
        apps_path = self.target.get_apps_path()
        
        for conn_name in connectors:
            conn_info = self.catalog.get_connector(conn_name)
            if not conn_info:
                results.append(f"{conn_name.ljust(15)} ERRO: Conector inexistente")
                continue
                
            provider = conn_info.get("provider")
            
            if not self._check_dependency(provider):
                results.append(f"{conn_name.ljust(15)} ERRO: Docker offline")
                continue
            
            try:
                if provider == "winget":
                    res = self.winget.install(conn_name, conn_info)
                elif provider == "docker":
                    res = self.docker.install(conn_name, conn_info)
                elif provider == "git":
                    res = self.git.install(conn_name, conn_info, apps_path)
                else:
                    res = "ERRO: Provider desconhecido"
            except Exception as e:
                res = f"ERRO CRÍTICO: {str(e)}"
                
            results.append(f"{conn_name.ljust(15)} {res}")
            
        # EMITE EVENTO NO BARRAMENTO EM VEZ DE CHAMAR O LOGS DIRETAMENTE
        if self.event_bus:
            self.event_bus.publish("INSTALL_COMPLETED", {"package": pkg_name, "results": results})
            
        return f"Missão '{pkg_name}' concluída!\n" + "\n".join(results)