import asyncio
import urllib.request
import json
import logging
from typing import Any, Optional
from .interfaces import IModelsService

logger = logging.getLogger(__name__)

class ModelsEngine(IModelsService):
    def __init__(self):
        self._knowledge_engine = None  # injetado depois via set_knowledge_engine()

    def set_knowledge_engine(self, knowledge_engine) -> None:
        """Chamado pelo kernel.py depois que o Planner é criado, pra evitar
        que este serviço abra um client ChromaDB concorrente com o do
        KnowledgeEngine — ambos NUNCA devem ter client próprio pra mesma pasta."""
        self._knowledge_engine = knowledge_engine

    async def get_model_and_rag_status(self) -> dict[str, Any]:
        loop = asyncio.get_running_loop()

        def check_models():
            models = []
            try:
                with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
                    data = json.loads(r.read().decode())
                    models = [m["name"] for m in data.get("models", [])]
            except Exception:
                pass
            return models

        models = await loop.run_in_executor(None, check_models)

        rag_docs = 0
        if self._knowledge_engine is not None:
            rag_docs = await loop.run_in_executor(None, self._knowledge_engine.get_document_count)
        else:
            logger.warning("ModelsEngine: knowledge_engine ainda não injetado — rag_docs retornando 0.")

        return {"models": models, "rag_docs": rag_docs}