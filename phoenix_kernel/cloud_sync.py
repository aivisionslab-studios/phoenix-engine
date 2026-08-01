import asyncio
import json
import logging
import os
import socket
import uuid
from pathlib import Path

# Importa os caminhos centralizados do módulo do Kernel
from phoenix_kernel.paths import FIRESTORE_CREDENTIALS, MACHINE_ID_FILE, CONSENT_FLAG, KNOWLEDGE_BASE_JSON

logger = logging.getLogger(__name__)

FIRESTORE_ROOT_COLLECTION = "phoenix_machines"
FIRESTORE_SUBCOLLECTION = "knowledge_base"
BATCH_SIZE = 400

def has_consent() -> bool:
    return CONSENT_FLAG.exists()

def grant_consent() -> None:
    CONSENT_FLAG.parent.mkdir(parents=True, exist_ok=True)
    CONSENT_FLAG.write_text("accepted")

def revoke_consent() -> None:
    if CONSENT_FLAG.exists():
        CONSENT_FLAG.unlink()

def get_or_create_machine_id() -> str:
    """Id estável dessa instalação da Phoenix."""
    if MACHINE_ID_FILE.exists():
        existing = MACHINE_ID_FILE.read_text().strip()
        if existing:
            return existing
    machine_id = str(uuid.uuid4())
    MACHINE_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    MACHINE_ID_FILE.write_text(machine_id)
    return machine_id

class FirestoreSync:
    def __init__(self):
        self._client = None
        self.machine_id = get_or_create_machine_id()

    def _get_client(self):
        if self._client is not None:
            return self._client

        from google.cloud import firestore
        from google.oauth2 import service_account

        env_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

        if env_json:
            info = json.loads(env_json)
            credentials = service_account.Credentials.from_service_account_info(info)
            project_id = info.get("project_id")
        elif env_path and Path(env_path).exists():
            credentials = service_account.Credentials.from_service_account_file(env_path)
            project_id = json.loads(Path(env_path).read_text(encoding="utf-8")).get("project_id")
        else:
            if not FIRESTORE_CREDENTIALS.exists():
                raise FileNotFoundError(
                    f"Nenhuma credencial do Firebase encontrada. Rodando local: salva o JSON "
                    f"de service account em '{FIRESTORE_CREDENTIALS}'. Em produção/deploy: "
                    f"defina a variável de ambiente FIREBASE_SERVICE_ACCOUNT_JSON."
                )
            credentials = service_account.Credentials.from_service_account_file(str(FIRESTORE_CREDENTIALS))
            project_id = json.loads(FIRESTORE_CREDENTIALS.read_text(encoding="utf-8")).get("project_id")

        self._client = firestore.Client(project=project_id, credentials=credentials)
        return self._client

    async def sync_knowledge_base(self) -> int:
        if not has_consent(): return 0
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_kb_blocking)

    def _sync_kb_blocking(self) -> int:
        if not KNOWLEDGE_BASE_JSON.exists(): return 0

        with open(KNOWLEDGE_BASE_JSON, "r", encoding="utf-8") as f:
            documents = json.load(f)
        if isinstance(documents, dict): documents = [documents]
        if not documents: return 0

        try:
            client = self._get_client()
            from google.cloud import firestore
            collection = client.collection(FIRESTORE_ROOT_COLLECTION).document(self.machine_id).collection(FIRESTORE_SUBCOLLECTION)

            sent = 0
            batch = client.batch()
            pending = 0
            for doc in documents:
                doc_id = doc.get("id")
                if not doc_id: continue
                batch.set(collection.document(doc_id), doc)
                sent += 1
                pending += 1
                if pending >= BATCH_SIZE:
                    batch.commit(); batch = client.batch(); pending = 0
            if pending: batch.commit()

            client.collection(FIRESTORE_ROOT_COLLECTION).document(self.machine_id).set(
                {"last_synced_at": firestore.SERVER_TIMESTAMP, "document_count": sent}, merge=True
            )
            logger.info(f"FirestoreSync: {sent} documento(s) do RAG sincronizado(s).")
            return sent
        except Exception as e:
            logger.error(f"FirestoreSync: Falha ao sincronizar RAG - {e}")
            return 0

    async def sync_machine_state(self, state_data: dict):
        if not has_consent(): return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._sync_state_blocking, state_data)

    def _sync_state_blocking(self, state_data: dict):
        try:
            client = self._get_client()
            from google.cloud import firestore
            doc_ref = client.collection(FIRESTORE_ROOT_COLLECTION).document(self.machine_id)
            doc_ref.set({
                "hostname": socket.gethostname(),
                "online": True,
                "last_seen": firestore.SERVER_TIMESTAMP,
                "phoenix_version": "5.0.0",
                "hardware": state_data.get("hardware", {}),
                "budget": state_data.get("budget", {}),
                "telemetry_enabled": True
            }, merge=True)
            telemetry = state_data.get("telemetry", {})
            if telemetry:
                doc_ref.collection("telemetry").add({**telemetry, "timestamp": firestore.SERVER_TIMESTAMP})
        except Exception as e:
            logger.debug(f"FirestoreSync: Erro ao sincronizar telemetria - {e}")

    async def add_log(self, level: str, service: str, message: str):
        if not has_consent(): return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._add_log_blocking, level, service, message)

    def _add_log_blocking(self, level: str, service: str, message: str):
        try:
            client = self._get_client()
            from google.cloud import firestore
            doc_ref = client.collection(FIRESTORE_ROOT_COLLECTION).document(self.machine_id)
            doc_ref.collection("logs").add({
                "level": level, "service": service, "message": message, "timestamp": firestore.SERVER_TIMESTAMP
            })
        except Exception:
            pass

    def shutdown(self):
        if not has_consent(): return
        try:
            client = self._get_client()
            from google.cloud import firestore
            doc_ref = client.collection(FIRESTORE_ROOT_COLLECTION).document(self.machine_id)
            doc_ref.set({"online": False, "last_seen": firestore.SERVER_TIMESTAMP}, merge=True)
        except Exception:
            pass