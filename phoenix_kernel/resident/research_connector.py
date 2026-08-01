import logging
import asyncio

logger = logging.getLogger(__name__)

class ResearchConnector:
    """Ferramenta controlada de pesquisa. No futuro, vai conectar ao SearXNG/HuggingFace.
    Por enquanto, usa regras simbólicas para validar compatibilidade."""

    async def search(self, query: str, hardware: dict) -> dict:
        logger.info(f"ResearchConnector: Pesquisando '{query}' para hardware {hardware.get('gpu')}")
        await asyncio.sleep(1) # Simula latência de rede
        
        vram = hardware.get("vram_mb", 0)
        gpu = hardware.get("gpu", "").lower()
        
        result = {
            "query": query,
            "found": True,
            "software": "llama.cpp (Vulkan)",
            "version": "b3600",
            "vulkan_compatible": "vulkan" in hardware.get("backends", []),
            "docker_needed": True,
            "notes": "Otimizado para GPUs AMD legacy via Vulkan."
        }
        
        if "image" in query or "flux" in query:
            result["software"] = "ComfyUI + stable-diffusion.cpp"
            result["vram_required"] = 6000
            
        return result
