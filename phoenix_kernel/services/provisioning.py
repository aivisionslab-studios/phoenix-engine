import os
import subprocess
import urllib.request
import logging
import sys
from pathlib import Path
from .catalog import CatalogEngine

logger = logging.getLogger(__name__)

class ProvisioningManager:
    def __init__(self):
        self.catalog = CatalogEngine()

    def install(self, connector_name: str) -> str:
        conn_info = self.catalog.get_connector(connector_name)
        if not conn_info: return f"[ERRO] Conector '{connector_name}' não existe no catálogo."
        provider = conn_info.get("provider")
        if provider == "docker": return self._install_docker(connector_name, conn_info)
        elif provider == "git": return self._install_git(connector_name, conn_info)
        elif provider == "winget": return self._install_winget(connector_name, conn_info)
        elif provider == "pip": return self._install_pip(connector_name, conn_info)
        else: return f"[ERRO] Provider '{provider}' não suportado."

    def _install_docker(self, name, info):
        cmd = ["docker", "run", "-d", f"--name={name}", f"--restart={info.get('restart', 'unless-stopped')}"]
        for p in info.get("ports", []): cmd.extend(["-p", p])
        for v in info.get("volumes", []): cmd.extend(["-v", v])
        cmd.append(info.get("image"))
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            subprocess.run(["docker", "start", name], capture_output=True, text=True, timeout=30)
            return f"[OK] Container '{name}' subiu."
        except Exception as e: return f"[ERRO] Docker: {e}"

    # Mapa de repositórios que precisam ser compilados com Vulkan, e a flag
    # CMake correta pra cada um (cada projeto ggml-based usa um nome de flag
    # próprio - GGML_VULKAN pro llama.cpp, SD_VULKAN pro stable-diffusion.cpp).
    # Adicionar um novo repo compilável = adicionar uma linha aqui.
    _VULKAN_BUILD_TARGETS = {
        "llama": "GGML_VULKAN",
        "stable-diffusion": "SD_VULKAN",
    }

    def _install_git(self, name, info):
        url = info.get("url")
        if not url: return "[ERRO] URL Git vazia"
        dest = Path("repos") / name

        # 1. Clona ou atualiza o repositório.
        # --recursive é obrigatório pro stable-diffusion.cpp (submódulos
        # ggml/libwebp/libwebm) e inofensivo pro llama.cpp (não tem
        # submódulos hoje, mas não quebra nada se tivesse).
        if dest.exists():
            subprocess.run(["git", "-C", str(dest), "pull"], capture_output=True, text=True, timeout=60)
            subprocess.run(["git", "-C", str(dest), "submodule", "update", "--init", "--recursive"],
                            capture_output=True, text=True, timeout=180)
        else:
            subprocess.run(["git", "clone", "--recursive", url, str(dest)], capture_output=True, text=True, timeout=300)

        # 2. RECEITA DE BOLO: se o repo estiver no mapa, compila com Vulkan.
        vulkan_flag = next((flag for key, flag in self._VULKAN_BUILD_TARGETS.items() if key in name.lower()), None)
        if vulkan_flag:
            logger.info("Provisioning: Compilando %s com Vulkan (CMake, -D%s=ON)...", name, vulkan_flag)
            build_dir = dest / "build"
            build_dir.mkdir(exist_ok=True)

            configure_cmd = ["cmake", "..", f"-D{vulkan_flag}=ON"]
            if os.name == "nt":
                # MSVC-only: stable-diffusion.cpp junta muitos modelos (SD,
                # Flux, Qwen Image...) num único .cpp gigante e estoura o
                # limite de seções de um objeto COFF (erro C1128). /bigobj
                # levanta esse limite. Não existe em GCC/Clang, por isso só
                # entra no Windows - noutro SO quebraria a build.
                configure_cmd.append("-DCMAKE_CXX_FLAGS=/bigobj")

            try:
                # shell=True com lista de argumentos é um bug em POSIX: só o
                # primeiro item roda como comando, o resto vira argumento do
                # próprio shell (não do cmake) e é silenciosamente ignorado.
                # Sem shell=True funciona igual nas duas plataformas.
                subprocess.run(configure_cmd, cwd=str(build_dir), check=True, timeout=120)
                # --parallel: sem isso o CMake não paraleliza builds MSBuild/MSVC
                # (compila essencialmente em single-thread mesmo com 24 threads
                # disponíveis no Xeon). O arquivo gigante do stable-diffusion.cpp
                # (o mesmo que estourou o C1128) pode passar de 10 min assim,
                # matando o processo pelo timeout sem erro claro no log.
                # Timeout subiu de 600s pra 1800s (30 min) por segurança mesmo
                # com paralelismo - build C++ real varia bastante por máquina.
                subprocess.run(
                    ["cmake", "--build", ".", "--config", "Release", "--parallel"],
                    cwd=str(build_dir), check=True, timeout=1800,
                )
                return f"[OK] Repo '{name}' clonado e COMPILADO com Vulkan com sucesso!"
            except subprocess.CalledProcessError as e:
                return f"[ERRO] Falha ao compilar {name}: {e}"
            except Exception as e:
                return f"[ERRO] Tempo limite ou outro erro na compilação: {e}"

        return f"[OK] Repo '{name}' clonado."

    def _install_winget(self, name, info):
        winget_id = info.get("winget_id")
        try:
            subprocess.run(["winget", "install", "--id", winget_id, "--accept-package-agreements", "--accept-source-agreements"], capture_output=True, text=True, timeout=300)
            return f"[OK] Winget '{name}' instalado."
        except Exception as e: return f"[ERRO] Winget: {e}"

    def _install_pip(self, name, info):
        pip_package = info.get("pip_package", name)
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", pip_package], capture_output=True, text=True, timeout=120)
            return f"[OK] Pip '{pip_package}' instalado."
        except Exception as e: return f"[ERRO] Pip: {e}"