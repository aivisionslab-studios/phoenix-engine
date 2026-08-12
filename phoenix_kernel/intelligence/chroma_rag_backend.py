"""
chroma_rag_backend.py

PHX-FIX (auditoria 2026-08-04): implementação real do `RagBackend` (Protocol
definido em `phoenix_kernel/planner/knowledge_engine.py` e duplicado em
`phoenix_kernel/intelligence/knowledge_engine.py`). Até agora nenhuma classe
concreta existia — os dois `KnowledgeEngine(...)` eram sempre instanciados
sem `rag_backend`, então `search_rag()`/`query_knowledge()` sempre retornavam
`[]`, mesmo com `data/chroma_db` já tendo uma coleção real com 226 documentos
(`aivisions_knowledge_base`, resultado da curadoria de ~91 entradas de
`knowledge_base.json`, expandida em chunks). Esta classe conecta nessa
coleção existente em vez de criar uma nova vazia.

Requer o pacote `chromadb` (já instalado pelo instalador em
install/common.ps1: `pip install ... chromadb ...`).

NOTA IMPORTANTE SOBRE OFFLINE: por padrão o ChromaDB usa sua
`DefaultEmbeddingFunction` (all-MiniLM-L6-v2 em ONNX), que baixa o modelo
(~90MB) de `chroma-onnx-models.s3.amazonaws.com` na PRIMEIRA vez que for
usada, e depois fica em cache local (`~/.cache/chroma/onnx_models/`). Isso
é uma dependência de rede pontual (não recorrente) que vale notar num
projeto pensado para inferência local/offline - se quiser eliminá-la
completamente, dá pra trocar por um embedding function que rode via
llama.cpp localmente, mas isso é uma mudança maior e fica fora do escopo
deste conserto (ver observação no relatório de auditoria).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from phoenix_kernel.intelligence.memory_loader import MemoryCard

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION_NAME = "aivisions_knowledge_base"


class ChromaRagBackend:
    """Implementação de `RagBackend` sobre um ChromaDB persistente local.

    Satisfaz o Protocol definido em ambas as cópias de `KnowledgeEngine`:
        def query(self, text: str, n_results: int = 3) -> list[str]: ...
        def upsert(self, cards: list[MemoryCard]) -> None: ...
    """

    def __init__(
        self,
        persist_dir: str | Path = "data/chroma_db",
        collection_name: str = DEFAULT_COLLECTION_NAME,
        embedding_function=None,
    ) -> None:
        self._persist_dir = Path(persist_dir)
        self._collection_name = collection_name
        self._embedding_function = embedding_function
        self._client = None
        self._collection = None
        self._unavailable_reason: str | None = None
        self._connect()

    def _connect(self) -> None:
        try:
            import chromadb  # import tardio: não derruba o boot se faltar o pacote
        except ImportError:
            self._unavailable_reason = (
                "Pacote 'chromadb' não instalado. Rode: pip install chromadb"
            )
            logger.warning("ChromaRagBackend: %s", self._unavailable_reason)
            return

        try:
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self._persist_dir))
            # get_or_create: conecta na coleção já existente (226 docs) se
            # houver, ou cria uma nova vazia na primeira execução limpa.
            kwargs = {"name": self._collection_name, "metadata": {"hnsw:space": "cosine"}}
            if self._embedding_function is not None:
                kwargs["embedding_function"] = self._embedding_function
            self._collection = self._client.get_or_create_collection(**kwargs)
            doc_count = self._collection.count()
            logger.info(
                "ChromaRagBackend: conectado a '%s' em %s (%d documentos).",
                self._collection_name, self._persist_dir, doc_count,
            )

            # PHX-FIX (achado real em produção): a coleção pode já ter sido
            # criada por outro pipeline de ingestão usando uma embedding
            # function diferente (ex: nomic-embed-text/bge-base, 768 dims),
            # enquanto get_or_create_collection() aqui, sem embedding_function
            # explícita, usa o DefaultEmbeddingFunction do Chroma (all-MiniLM
            # -L6-v2, 384 dims). Nesse caso TODA chamada a .query() explode
            # com "InvalidArgumentError: dimension of 768, got 384" - e como
            # o método query() abaixo tem um try/except amplo, isso virava
            # um crash-loop silencioso (uma inferência ONNX inteira + um
            # traceback completo a cada chamada, sem nunca dizer o motivo
            # real). Faz um probe de verdade AGORA, uma única vez, pra falhar
            # cedo com uma mensagem clara em vez de repetir o erro sempre.
            if doc_count > 0:
                try:
                    self._collection.query(query_texts=["probe de dimensão de embedding"], n_results=1)
                except Exception as probe_exc:
                    dim_match = re.search(r"dimension of (\d+), got (\d+)", str(probe_exc))
                    if dim_match:
                        self._unavailable_reason = (
                            f"Coleção '{self._collection_name}' foi criada com embeddings de "
                            f"{dim_match.group(1)} dimensões, mas a embedding function atual gera "
                            f"{dim_match.group(2)} dimensões (provavelmente um outro script de "
                            f"ingestão usou um modelo de embedding diferente). Os "
                            f"{doc_count} documentos existentes ficam inacessíveis até você: "
                            f"(1) reconectar com a embedding_function original que gerou os "
                            f"{dim_match.group(1)}-dim vectors, ou (2) apagar '{self._persist_dir}' "
                            f"e reingerir do zero com a embedding function atual."
                        )
                    else:
                        self._unavailable_reason = f"Probe de conexão falhou: {probe_exc}"
                    logger.error("ChromaRagBackend: %s", self._unavailable_reason)
                    self._collection = None
        except Exception as e:
            self._unavailable_reason = f"Falha ao conectar no ChromaDB em {self._persist_dir}: {e}"
            logger.error("ChromaRagBackend: %s", self._unavailable_reason, exc_info=True)
            self._client = None
            self._collection = None

    @property
    def available(self) -> bool:
        return self._collection is not None

    def count(self) -> int:
        if not self.available:
            return 0
        try:
            return self._collection.count()
        except Exception:
            logger.warning("ChromaRagBackend: falha ao contar documentos.", exc_info=True)
            return 0

    def query(self, text: str, n_results: int = 3) -> list[str]:
        """Retorna os `n_results` documentos mais similares como list[str]
        (contrato do RagBackend). Nunca levanta exceção para o chamador —
        RAG é um "nice to have" no contexto do LLM, uma falha aqui não pode
        derrubar o resto do build_context()/plan_mission()."""
        if not self.available:
            if self._unavailable_reason:
                logger.warning("ChromaRagBackend.query: indisponível (%s).", self._unavailable_reason)
            return []
        if not text or not text.strip():
            return []
        try:
            result = self._collection.query(query_texts=[text], n_results=max(1, n_results))
        except Exception:
            logger.error("ChromaRagBackend.query: falha ao consultar ChromaDB.", exc_info=True)
            return []

        documents = result.get("documents") or []
        if not documents:
            return []
        # query_texts=[text] com um único item -> documents é list[list[str]]
        # de tamanho 1; documents[0] são os hits para essa única query.
        return list(documents[0])

    def upsert(self, cards: "list[MemoryCard]") -> None:
        """Insere/atualiza os MemoryCards no ChromaDB. Usa `source_id`
        (caminho relativo estável) como id do documento, garantindo que
        reingestões subsequentes atualizem em vez de duplicar."""
        if not self.available:
            raise RuntimeError(
                f"ChromaRagBackend indisponível para upsert: {self._unavailable_reason or 'motivo desconhecido'}"
            )
        if not cards:
            return

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []
        for card in cards:
            ids.append(card.source_id)
            documents.append(card.content)
            # ChromaDB não aceita valores None/list/dict em metadata - só
            # str/int/float/bool. Achata tags em string e descarta o resto
            # do metadata livre (fica só no MemoryCard, não precisa ir pro
            # índice vetorial).
            metadatas.append({
                "layer": card.layer,
                "title": card.title,
                "tags": ",".join(card.tags) if card.tags else "",
            })

        try:
            self._collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        except Exception as e:
            raise RuntimeError(f"Falha ao fazer upsert de {len(cards)} card(s) no ChromaDB: {e}") from e


# PHX-FIX (auditoria 2026-08-09): PlannerEngine (phoenix_kernel/planner/engine.py)
# e ReasoningEngine (phoenix_kernel/intelligence/reasoning_engine.py) cada um
# instanciava seu próprio `ChromaRagBackend(persist_dir="data/chroma_db")`
# de forma independente - dois clientes ChromaDB persistentes separados
# (cada um com seu próprio handle de SQLite/HNSW) apontando pro MESMO
# diretório, dentro do MESMO processo. ChromaDB PersistentClient não foi
# desenhado pra múltiplas instâncias concorrentes no mesmo path dentro de
# um processo (é o motivo pelo qual os testes de boot já precisam rodar em
# diretório isolado pra não corromper o índice HNSW - ver regra do projeto).
# Se `infer` e `resident research` forem usados em sequência rápida, os dois
# clientes competem pelo mesmo lock de SQLite. Esta função dá um singleton
# por processo por (persist_dir, collection_name), pra qualquer parte do
# kernel que precise de RAG reusar a mesma conexão em vez de abrir outra.
_shared_backends: dict[tuple[str, str], "ChromaRagBackend"] = {}


def get_shared_chroma_backend(
    persist_dir: str | Path = "data/chroma_db",
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> "ChromaRagBackend":
    """Retorna uma instância única de ChromaRagBackend por (persist_dir,
    collection_name) dentro do processo atual. Use isto em vez de
    `ChromaRagBackend(...)` diretamente sempre que mais de um subsistema
    (planner, resident/reasoning, etc.) puder precisar do mesmo índice."""
    key = (str(Path(persist_dir)), collection_name)
    if key not in _shared_backends:
        _shared_backends[key] = ChromaRagBackend(
            persist_dir=persist_dir, collection_name=collection_name
        )
    return _shared_backends[key]
