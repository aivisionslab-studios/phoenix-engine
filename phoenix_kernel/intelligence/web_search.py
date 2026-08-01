import logging
import httpx

logger = logging.getLogger(__name__)

SEARXNG_URL = "http://localhost:8080/search"

# Cabeçalho para fingir ser um navegador real e bypassar o anti-bot (erro 403) do SearXNG
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Real-IP": "127.0.0.1"  # Resolve o erro 'X-Forwarded-For nor X-Real-IP header is set!'
}

async def search_web(query: str, max_results: int = 3) -> str:
    """Busca na internet usando a instância local do SearXNG."""
    logger.info(f"[WebSearch] Buscando na internet: '{query}'")
    
    params = {"q": query, "format": "json", "categories": "general"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(SEARXNG_URL, params=params, headers=HEADERS)
            resp.raise_for_status()
            data = resp.json()
            
            results = data.get("results", [])
            if not results:
                return "Nenhum resultado encontrado na web."
                
            text_results = []
            for r in results[:max_results]:
                title = r.get("title", "")
                content = r.get("content", "")
                text_results.append(f"- {title}: {content}")
                
            logger.info("[WebSearch] Busca concluída via SearXNG local.")
            return "\n".join(text_results)
            
    except Exception as e:
        logger.error(f"[WebSearch] Falha ao buscar no SearXNG: {e}")
        return f"Falha ao acessar a internet (SearXNG): {e}"