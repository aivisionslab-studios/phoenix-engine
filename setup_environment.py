import os
import json
from pathlib import Path

def create_file(path: str, content: str):
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    print(f"[OK] Arquivo criado/atualizado: {filepath}")

def create_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)
    print(f"[OK] Pasta garantida: {path}")

print("="*50)
print(" CONFIGURANDO AMBIENTE PHOENIX 5.0")
print("="*50)

# 1. Estrutura de Pastas
dirs = [
    "catalog/packages/essentials",
    "catalog/packages/studios",
    "catalog/packages/suites",
    "catalog/packages/addons",
    "knowledge/intrinsic",
    "knowledge/procedures",
    "knowledge/machine",
    "rag/source_docs",
    "repos",
    "logs/install"
]
for d in dirs:
    create_dir(d)

# 2. Catálogos JSON
connectors_json = {
    "ollama": {
        "name": "Ollama Engine", "provider": "docker", "image": "ollama/ollama:latest",
        "ports": ["11434:11434"], "volumes": ["ollama:/root/.ollama"], "restart": "unless-stopped"
    },
    "open-webui": {
        "name": "Open WebUI", "provider": "docker", "image": "ghcr.io/open-webui/open-webui:main",
        "ports": ["3000:8080"], "volumes": ["open-webui:/app/backend/data"], "restart": "unless-stopped",
        "environment": {"OLLAMA_BASE_URL": "http://host.docker.internal:11434"}
    },
    "stable-diffusion.cpp": {
        "name": "Stable Diffusion.cpp (Vulkan)", "provider": "git", "url": "https://github.com/leejet/stable-diffusion.cpp.git"
    },
    "comfyui": {
        "name": "ComfyUI", "provider": "git", "url": "https://github.com/comfyanonymous/ComfyUI.git"
    },
    "lm_studio": {
        "name": "LM Studio", "provider": "winget", "winget_id": "ElementLabs.LMStudio"
    },
    "openai_api": {
        "name": "OpenAI API Client", "provider": "pip", "pip_package": "openai"
    },
    "mcp": {
        "name": "Model Context Protocol (MCP)", "provider": "pip", "pip_package": "mcp"
    }
}
create_file("catalog/connectors.json", json.dumps(connectors_json, indent=2, ensure_ascii=False))

models_json = {
    "flux": {
        "name": "FLUX.1-schnell (GGUF Q4)", "url": "https://huggingface.co/lllab/flux_gguf/resolve/main/flux1-schnell-Q4_0.gguf",
        "type": "image", "destination_folder": "StableDiffusion", "filename": "flux1-schnell-Q4_0.gguf"
    },
    "qwen3:8b": {
        "name": "Qwen3 8B (Ollama)", "url": "ollama://qwen3:8b", "type": "llm"
    }
}
create_file("catalog/models.json", json.dumps(models_json, indent=2, ensure_ascii=False))

# 3. Arquivos Python do Kernel (Provisioning, Models, etc.)
# (Conteúdos exatos para colar nos arquivos)

PROVISIONING_PY = '''import subprocess
import urllib.request
import logging
import sys
from pathlib import Path
from .catalog import CatalogEngine

logger = logging.getLogger(__name__)

class ProvisioningManager:
    def __init__(self):
        self.catalog = CatalogEngine()

    async def install(self, connector_name: str) -> str:
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

    def _install_git(self, name, info):
        url = info.get("url")
        if not url: return "[ERRO] URL Git vazia"
        dest = Path("repos") / name
        if dest.exists():
            subprocess.run(["git", "-C", str(dest), "pull"], capture_output=True, text=True, timeout=60)
            return f"[OK] Repo '{name}' atualizado."
        try:
            subprocess.run(["git", "clone", url, str(dest)], capture_output=True, text=True, timeout=180)
            return f"[OK] Repo '{name}' clonado."
        except Exception as e: return f"[ERRO] Git: {e}"

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
'''

MODEL_MANAGER_PY = '''import os
import json
import logging
import asyncio
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self):
        self.catalog_path = Path("catalog/models.json")
        self.storage_path = Path(os.environ.get("PHOENIX_STORAGE_JSON", "C:/ProgramData/Phoenix/storage.json"))
        
    def _get_models_base_dir(self) -> Path:
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    storage = json.load(f)
                workspace = Path(storage.get("workspace", "E:\\\\Phoenix"))
                return workspace / "Models"
        except: pass
        return Path("E:/Phoenix/Models")

    async def download_model(self, model_id: str) -> Path | None:
        """CONTRATO: devolve Path existente em sucesso, None em erro/ollama-only.
        NUNCA string de log - o LlamaCppDriver depende disso pra decidir
        entre rodar nativo (Vulkan) ou cair no fallback Ollama."""
        if not self.catalog_path.exists():
            logger.error("ModelManager: catalog/models.json não encontrado.")
            return None
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        model_info = catalog.get(model_id)
        if not model_info:
            logger.error("ModelManager: modelo '%s' não encontrado no catálogo.", model_id)
            return None
        url = model_info.get("url")

        if url and url.startswith("ollama://"):
            ollama_model = url.replace("ollama://", "")
            proc = await asyncio.create_subprocess_exec("docker", "exec", "ollama", "ollama", "pull", ollama_model)
            await proc.communicate()
            if proc.returncode != 0:
                logger.error("ModelManager: pull do Ollama '%s' falhou (rc=%s).", ollama_model, proc.returncode)
            else:
                logger.info("ModelManager: modelo Ollama '%s' baixado.", ollama_model)
            return None

        base_dir = self._get_models_base_dir()
        dest_folder = base_dir / model_info.get("destination_folder", "")
        dest_folder.mkdir(parents=True, exist_ok=True)
        dest_file = dest_folder / model_info.get("filename", "model.bin")

        if dest_file.exists():
            logger.info("ModelManager: modelo já existe em %s.", dest_file)
            return dest_file

        tmp_file = dest_file.with_suffix(dest_file.suffix + ".part")
        logger.info(f"Baixando {url} -> {dest_file}")
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                async with client.stream("GET", url, timeout=600.0) as resp:
                    resp.raise_for_status()
                    with open(tmp_file, "wb") as f:
                        async for chunk in resp.aiter_bytes(): f.write(chunk)
            tmp_file.rename(dest_file)
            logger.info("ModelManager: modelo salvo em %s.", dest_file)
            return dest_file
        except Exception as e:
            logger.error("ModelManager: falha no download de '%s': %s", model_id, e)
            tmp_file.unlink(missing_ok=True)
            return None
'''

create_file("phoenix_kernel/07_services/provisioning.py", PROVISIONING_PY)
create_file("phoenix_kernel/08_models/model_manager.py", MODEL_MANAGER_PY)

print("\n[✓] AMBIENTE CONFIGURADO COM SUCESSO!")
print("Agora basta reiniciar a API: python api_server.py")