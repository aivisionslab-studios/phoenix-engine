from __future__ import annotations
import asyncio
import json
import hashlib
import urllib.request
import urllib.error
import logging
import os
from pathlib import Path
from typing import Any, Optional

import chromadb
from chromadb.config import Settings

from core.contracts.engine import IEngine
from core.domain.engine import EngineDescriptor, HealthStatus, Capability
from core.events.bus import EventBus
from core.kernel.kernel import PlatformKernel

logger = logging.getLogger(__name__)

RECOMMENDATION_THRESHOLD = 0.45
COLLECTION_NAME = "aivisions_knowledge_base"


# ============================================================================
# Geração de texto pra embedding, por categoria.
#
# ANTES: text = ". ".join(f"{k}: {v}" for k, v in doc.items()) — pra campos
# aninhados (a maioria dos documentos), isso vira repr de dict do Python tipo
# "hardware: {'gpu': 'AMD Radeon RX 580', 'vram_mb': 8192, ...}". Isso não é
# linguagem natural, é sintaxe — o modelo de embedding (nomic-embed-text) via
# de forma parecida em quase todo documento (mesma estrutura de chaves/aspas),
# então a similaridade ficava sempre numa faixa estreita (~0.6) não importa a
# query, porque o "ruído de formatação" dominava o sinal semântico real.
#
# AGORA: cada categoria vira uma frase em português, junta os campos que
# fazem sentido juntos. Categoria sem builder dedicado cai no fallback
# genérico (_generic_doc_text), que pelo menos remove a sintaxe de dict e
# vira "chave.subchave: valor" — já uma melhora bem maior que o repr cru.
# ============================================================================

def _safe_join(items) -> str:
    return ", ".join(str(i) for i in items) if items else ""


def _benchmark_text(doc: dict) -> str:
    hw = doc.get("hardware", {}) or {}
    model = doc.get("model", {}) or {}
    test = doc.get("test", {}) or {}
    meta = doc.get("metadata", {}) or {}
    cfg = test.get("configuration", {}) or {}
    cfg_flags = [k for k, v in cfg.items() if v]

    parts = [
        f"Benchmark de {model.get('name', 'modelo desconhecido')} "
        f"({model.get('type', 'N/A')}, quantização {model.get('quantization', 'N/A')}, "
        f"{model.get('size_gb', '?')}GB)",
        f"rodando em {hw.get('gpu', 'N/A')} com {hw.get('vram_mb', '?')}MB VRAM "
        f"via backend {hw.get('backend', 'N/A')}",
        f"CPU {hw.get('cpu', 'N/A')}, {hw.get('ram_mb', '?')}MB RAM, SO {hw.get('os', 'N/A')}",
        f"teste em resolução {test.get('resolution')} com {test.get('steps', '?')} passos"
        if test.get("resolution") else "",
        f"resultado: {test.get('result', 'N/A')} em {test.get('duration_sec', '?')}s, "
        f"usando {test.get('vram_used_mb', '?')}MB VRAM e {test.get('ram_used_mb', '?')}MB RAM, "
        f"GPU a {test.get('gpu_temp_celsius', '?')}°C",
        f"opções ativas: {_safe_join(cfg_flags)}" if cfg_flags else "",
        f"fonte: {meta.get('source', '')}, confiança {meta.get('confidence', '')}" if meta else "",
    ]
    return ". ".join(p for p in parts if p)


def _problem_text(doc: dict) -> str:
    hw = doc.get("hardware", {}) or {}
    parts = [
        f"Problema conhecido: {doc.get('title', 'sem título')}",
        f"hardware: {hw.get('gpu', 'N/A')} em {hw.get('os', 'N/A')}" if hw else "",
        f"modelo: {doc.get('model')}" if doc.get("model") else "",
        f"erro: {doc.get('error', 'N/A')}",
        f"causa: {doc.get('cause', 'N/A')}",
        f"solução: {doc.get('solution', 'N/A')}",
        f"status: {doc.get('status', 'N/A')}",
        f"nota: {doc.get('notes')}" if doc.get("notes") else "",
    ]
    return ". ".join(p for p in parts if p)


def _rule_text(doc: dict) -> str:
    parts = [
        f"Regra: {doc.get('rule', 'N/A')}",
        f"contexto: {doc.get('context')}" if doc.get("context") else "",
        f"aplica-se a: {doc.get('applies_to')}" if doc.get("applies_to") else "",
    ]
    return ". ".join(p for p in parts if p)


def _configuration_text(doc: dict) -> str:
    flags = doc.get("flags", {}) or {}
    flags_txt = "; ".join(f"{k}: {v}" for k, v in flags.items())
    parts = [
        f"Configuração recomendada ({doc.get('recommendation_tier', 'N/A')}): {doc.get('name', 'sem nome')}",
        f"flags: {flags_txt}" if flags_txt else "",
        f"resultado: {doc.get('result', 'N/A')} em {doc.get('duration_sec', '?')}s, "
        f"{doc.get('vram_used_mb', '?')}MB VRAM, {doc.get('ram_used_mb', '?')}MB RAM",
        f"validado em: {doc.get('validated_on')}" if doc.get("validated_on") else "",
    ]
    return ". ".join(p for p in parts if p)


def _flatten_kv(prefix: str, value: Any, parts: list) -> None:
    """Fallback genérico: em vez de str(dict) (que vira repr com chaves/
    aspas), transforma em 'chave.subchave: valor', que pelo menos lê como
    texto e não como sintaxe."""
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten_kv(f"{prefix}.{k}" if prefix else k, v, parts)
    elif isinstance(value, list):
        if not value:
            return
        if isinstance(value[0], (dict, list)):
            for i, v in enumerate(value):
                _flatten_kv(f"{prefix}[{i}]", v, parts)
        else:
            parts.append(f"{prefix}: {_safe_join(value)}")
    else:
        if value not in (None, ""):
            parts.append(f"{prefix}: {value}")


def _generic_doc_text(doc: dict) -> str:
    parts = []
    for k, v in doc.items():
        if k in ("id", "category"):
            continue  # id/hash e a categoria (repetida em vários docs) não ajudam a discriminar
        _flatten_kv(k, v, parts)
    return ". ".join(parts)


def _telemetry_event_text(doc: dict) -> str:
    parts = [
        f"Evento de telemetria: {doc.get('title', 'sensor fora do normal')}",
        f"dispositivo: {doc.get('device', 'N/A')}",
        f"sensor: {doc.get('sensor_name', 'N/A')} ({doc.get('sensor_type', 'N/A')}) registrou "
        f"{doc.get('value', '?')}{doc.get('unit', '')}, limite considerado "
        f"{doc.get('threshold', '?')}{doc.get('unit', '')}",
        f"hardware da máquina: {doc.get('hardware_gpu')}" if doc.get("hardware_gpu") else "",
        f"observado em: {doc.get('first_observed')}" if doc.get("first_observed") else "",
        f"nota: {doc.get('notes')}" if doc.get("notes") else "",
    ]
    return ". ".join(p for p in parts if p)


_DOC_TEXT_BUILDERS = {
    "benchmark": _benchmark_text,
    "problem": _problem_text,
    "rule": _rule_text,
    "configuration": _configuration_text,
    "telemetry_event": _telemetry_event_text,
}


def _build_doc_text(doc: dict) -> str:
    category = doc.get("category", "")
    builder = _DOC_TEXT_BUILDERS.get(category)
    if builder:
        try:
            text = builder(doc)
            if text:
                return text
        except Exception:
            pass  # documento fora do formato esperado pra essa categoria -> cai pro genérico
    return _generic_doc_text(doc)


class KnowledgeEngine(IEngine):
    """Motor de RAG da Phoenix, agora sobre ChromaDB. Sincroniza
    data/knowledge_base.json com a coleção do Chroma (só re-vetoriza o
    que mudou, via hash), e responde consultas semânticas usando a busca
    vetorial nativa do Chroma em vez de um loop Python."""

    def __init__(
        self,
        event_bus: EventBus,
        kernel: PlatformKernel,
        chroma_path: str = "data/chroma_db",
        kb_json_path: str = "data/knowledge_base.json",
    ) -> None:
        self._event_bus = event_bus
        self._kernel = kernel
        self.chroma_path = chroma_path
        self.kb_json_path = kb_json_path
        self.ollama_url = "http://127.0.0.1:11434"
        self.embed_model = "nomic-embed-text"

        self._client: Optional[chromadb.ClientAPI] = None
        self._collection = None

        self._descriptor = EngineDescriptor(
            id="knowledge",
            name="AIVisions Knowledge Engine",
            version="3.1.0",
            sdk_version="1.0.0",
            capabilities=(Capability(name="rag", version="2.0"),),
        )

    @property
    def descriptor(self) -> EngineDescriptor:
        return self._descriptor

    def _embed(self, text: str) -> Optional[list]:
        payload = json.dumps({"model": self.embed_model, "input": text}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                embeddings = data.get("embeddings")
                if embeddings: return embeddings[0]
                single = data.get("embedding")
                if single: return single
                return None
        except Exception as e:
            logger.error(f"KnowledgeEngine: falha ao chamar Ollama /api/embed: {e}")
            return None

    async def initialize(self) -> None:
        logger.info("KnowledgeEngine: Initializing RAG system (ChromaDB backend)...")
        os.makedirs(self.chroma_path, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        kb_path = Path(self.kb_json_path)
        if not kb_path.exists():
            logger.warning(f"KnowledgeEngine: {self.kb_json_path} não encontrado.")
            return

        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                documents = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"KnowledgeEngine: JSON inválido ({e}). Abortando.")
            return

        if isinstance(documents, dict): documents = [documents]

        existing_data = self._collection.get(include=["metadatas"])
        existing = {
            doc_id: meta.get("content_hash")
            for doc_id, meta in zip(existing_data["ids"], existing_data["metadatas"])
        }

        synced, skipped, failed = 0, 0, 0

        for doc in documents:
            doc_id = doc.get("id") or hashlib.sha256(
                json.dumps(doc, sort_keys=True).encode()
            ).hexdigest()[:16]
            text = _build_doc_text(doc)
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

            if existing.get(doc_id) == content_hash:
                skipped += 1
                continue

            embedding = self._embed(text)
            if embedding is None:
                failed += 1
                continue

            self._collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[{
                    "category": doc.get("category", ""),
                    "content_hash": content_hash,
                    "original_json": json.dumps(doc, ensure_ascii=False),
                }],
            )
            synced += 1

        logger.info(
            f"KnowledgeEngine: sync concluído (ChromaDB). {synced} novo(s)/atualizado(s), "
            f"{skipped} inalterado(s), {failed} falha(s) de embedding."
        )

    async def query_knowledge(self, query_text: str, threshold: float = RECOMMENDATION_THRESHOLD) -> Optional[dict]:
        if self._collection is None: return None

        query_embedding = self._embed(query_text)
        if query_embedding is None: return None

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
            include=["metadatas", "distances"],
        )

        ids = results.get("ids", [[]])[0]
        if not ids: return None

        distance = results["distances"][0][0]
        similarity = 1.0 - distance
        metadata = results["metadatas"][0][0]
        doc_id = ids[0]

        if similarity < threshold:
            logger.info(f"KnowledgeEngine: melhor match '{doc_id}' ({similarity:.3f}) abaixo do threshold.")
            return None

        logger.info(f"KnowledgeEngine: documento recuperado -> {doc_id} (similaridade: {similarity:.3f})")
        result = json.loads(metadata["original_json"])
        result["_similarity_score"] = round(similarity, 4)
        return result

    async def has_document(self, doc_id: str) -> bool:
        """Verifica se um doc_id já existe na coleção — evita registrar a
        mesma observação de novo a cada ciclo do loop automático."""
        if self._collection is None:
            return False
        try:
            existing = self._collection.get(ids=[doc_id])
            return bool(existing.get("ids"))
        except Exception:
            return False

    async def add_document(self, doc: dict) -> bool:
        """Adiciona um documento novo ao RAG em tempo de execução (ex: o
        ResidentManager registrando um evento de sensor). Passa pelo MESMO
        _build_doc_text que o sync do knowledge_base.json usa — o documento
        vira embedding como frase natural por categoria, igual a tudo mais
        na base, nunca texto cru. Também persiste em disco (kb_json_path)
        pra sobreviver a um restart, mantendo o arquivo como fonte de
        verdade única em vez do documento existir só dentro do Chroma."""
        if self._collection is None:
            logger.warning("KnowledgeEngine: add_document chamado antes da coleção estar pronta.")
            return False

        doc_id = doc.get("id")
        if not doc_id:
            logger.warning("KnowledgeEngine: add_document precisa de um 'id' no documento.")
            return False

        text = _build_doc_text(doc)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        embedding = self._embed(text)
        if embedding is None:
            logger.warning(f"KnowledgeEngine: falha ao gerar embedding pra novo documento '{doc_id}'.")
            return False

        self._collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "category": doc.get("category", ""),
                "content_hash": content_hash,
                "original_json": json.dumps(doc, ensure_ascii=False),
            }],
        )

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._append_to_kb_file, doc)

        logger.info(f"KnowledgeEngine: novo documento adicionado ao RAG -> {doc_id}")
        return True

    def _append_to_kb_file(self, doc: dict) -> None:
        """Persiste o novo documento em data/knowledge_base.json (substitui
        se o id já existir lá). Roda em thread separada (chamado via
        run_in_executor) porque é I/O de disco bloqueante."""
        try:
            kb_path = Path(self.kb_json_path)
            documents = []
            if kb_path.exists():
                with open(kb_path, "r", encoding="utf-8") as f:
                    documents = json.load(f)
                if isinstance(documents, dict):
                    documents = [documents]
            documents = [d for d in documents if d.get("id") != doc.get("id")]
            documents.append(doc)
            with open(kb_path, "w", encoding="utf-8") as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"KnowledgeEngine: falha ao persistir novo documento em {self.kb_json_path}: {e}")

    def get_document_count(self) -> int:
        if self._collection is None:
            return 0
        try:
            return self._collection.count()
        except Exception as e:
            logger.warning(f"KnowledgeEngine: falha ao contar documentos: {e}")
            return 0

    async def health_check(self) -> HealthStatus:
        try:
            if self._collection is None: return HealthStatus(healthy=False, details="Não inicializada.")
            count = self._collection.count()
            return HealthStatus(healthy=True, details=f"{count} documento(s) indexado(s).")
        except Exception as e:
            return HealthStatus(healthy=False, details=str(e))

    async def shutdown(self) -> None:
        pass