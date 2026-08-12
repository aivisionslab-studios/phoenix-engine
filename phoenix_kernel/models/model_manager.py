import os
import json
import logging
import asyncio
import httpx
from pathlib import Path

# PHX-FIX: Importa o PhoenixPaths para centralizar a resolução de caminhos
from phoenix_kernel.paths import PhoenixPaths

logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self, workspace_path: Path = None):
        # PHX-FIX: Calcula a raiz do projeto dinamicamente (phoenix_kernel/models/ -> 3 níveis acima)
        project_root = Path(__file__).resolve().parent.parent.parent
        self.catalog_path = project_root / "catalog" / "models.json"

    async def download_model(self, model_id: str) -> Path | None:
        """Baixa (ou localiza) o modelo e devolve o Path físico do arquivo.

        CONTRATO: devolve um Path que existe em disco em caso de sucesso
        (baixado agora OU ja existente), e None em qualquer caso de erro.
        NUNCA devolve string de log - o ResidentManager e os Drivers
        dependem disso para decidir se podem rodar nativo (Vulkan).
        """
        if not self.catalog_path.exists():
            logger.error(f"ModelManager: {self.catalog_path} não encontrado.")
            return None
            
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
            
        model_info = catalog.get(model_id)
        if not model_info:
            logger.error(f"ModelManager: modelo '{model_id}' não encontrado no catálogo.")
            return None
            
        url = model_info.get("url")

        # Modelos Ollama-only não tem .gguf físico para devolver
        if url and url.startswith("ollama://"):
            ollama_model = url.replace("ollama://", "")
            proc = await asyncio.create_subprocess_exec(
                "docker", "exec", "ollama", "ollama", "pull", ollama_model
            )
            await proc.communicate()
            if proc.returncode != 0:
                logger.error("ModelManager: 'docker exec ollama pull %s' falhou (rc=%s).", ollama_model, proc.returncode)
            else:
                logger.info("ModelManager: modelo Ollama '%s' baixado.", ollama_model)
            return None

        # PHX-FIX: Usa PhoenixPaths para resolver a pasta de destino dinamicamente
        dest_folder_str = model_info.get("destination_folder", "")
        dest_folder = PhoenixPaths.get_models_base()
        if dest_folder_str:
            parts = dest_folder_str.split("/")
            for part in parts:
                dest_folder = dest_folder / part
                
        dest_folder.mkdir(parents=True, exist_ok=True)
        dest_file = dest_folder / model_info.get("filename", "model.bin")

        if dest_file.exists():
            logger.info(f"ModelManager: modelo já existe em {dest_file}")
            await self._download_components(model_info, dest_folder)
            return dest_file

        # Baixa para um .part e só renomeia no final - evita arquivos corrompidos
        tmp_file = dest_file.with_suffix(dest_file.suffix + ".part")
        logger.info(f"ModelManager: baixando {url} -> {dest_file}")
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                async with client.stream("GET", url, timeout=600.0) as resp:
                    resp.raise_for_status()
                    with open(tmp_file, "wb") as f:
                        async for chunk in resp.aiter_bytes():
                            f.write(chunk)
            tmp_file.rename(dest_file)
            logger.info(f"ModelManager: modelo salvo em {dest_file}")
            
            await self._download_components(model_info, dest_folder)
            return dest_file
        except Exception as e:
            logger.error(f"ModelManager: falha no download de '{model_id}': {e}")
            if tmp_file.exists():
                tmp_file.unlink()
            return None

    async def _download_components(self, model_info: dict, dest_folder: Path) -> None:
        """Baixa arquivos-companheiros do modelo principal (ex: VAE, CLIP-L, T5XXL)."""
        components = model_info.get("components")
        if not components:
            return
            
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for comp_name, comp_info in components.items():
                comp_url = comp_info.get("url")
                comp_file = dest_folder / comp_info.get("filename", f"{comp_name}.safetensors")
                
                if comp_file.exists():
                    continue
                    
                comp_tmp = comp_file.with_suffix(comp_file.suffix + ".part")
                logger.info(f"ModelManager: baixando componente '{comp_name}': {comp_url} -> {comp_file}")
                try:
                    async with client.stream("GET", comp_url, timeout=600.0) as resp:
                        resp.raise_for_status()
                        with open(comp_tmp, "wb") as f:
                            async for chunk in resp.aiter_bytes():
                                f.write(chunk)
                    comp_tmp.rename(comp_file)
                    logger.info(f"ModelManager: componente '{comp_name}' salvo em {comp_file}")
                except Exception as e:
                    logger.error(f"ModelManager: falha no download do componente '{comp_name}': {e}")
                    if comp_tmp.exists():
                        comp_tmp.unlink()