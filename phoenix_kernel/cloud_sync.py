import asyncio
import json
import logging
import os
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

# Onde tudo fica: o flag de consentimento, a credencial do Firebase, o id
# estável da máquina, e a base de RAG local que vai ser espelhada pro
# Firestore. Tudo relativo à raiz do projeto (mesmo padrão do
# LICENSE_ACCEPTED_FLAG no api_server.py).
CONSENT_FLAG_PATH = "data/telemetry_consent.flag"
CREDENTIALS_PATH = "data/firebase_service_account.json"
KB_JSON_PATH = "data/knowledge_base.json"
MACHINE_ID_PATH = "data/machine_id.txt"

FIRESTORE_ROOT_COLLECTION = "phoenix_machines"
FIRESTORE_SUBCOLLECTION = "knowledge_base"

# Limite real do Firestore é 500 escritas por batch. Corta bem antes disso
# pra sobrar folga (o carimbo de "last_synced_at" no fim de cada sync
# também conta como uma escrita).
BATCH_SIZE = 400


def has_consent() -> bool:
    return Path(CONSENT_FLAG_PATH).exists()


def grant_consent() -> None:
    p = Path(CONSENT_FLAG_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("accepted")


def revoke_consent() -> None:
    p = Path(CONSENT_FLAG_PATH)
    if p.exists():
        p.unlink()


def get_or_create_machine_id() -> str:
    """
    Id estável dessa instalação da Phoenix, só pra separar os dados de cada
    máquina dentro do mesmo projeto Firestore. Não depende do Discovery
    (que hoje não gera nenhum identificador próprio) — é um UUID gerado
    uma vez e salvo localmente; some se você apagar data/machine_id.txt.
    """
    p = Path(MACHINE_ID_PATH)
    if p.exists():
        existing = p.read_text().strip()
        if existing:
            return existing
    machine_id = str(uuid.uuid4())
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(machine_id)
    return machine_id


class FirestoreSync:
    """
    Sobe TODO o conteúdo de data/knowledge_base.json (benchmarks, problemas,
    regras, configurações, eventos de telemetria automáticos — tudo que já
    está no RAG local, sem filtro por categoria) pro Firestore, sempre sob
    o mesmo machine_id (separando os dados de cada instalação da Phoenix
    dentro do mesmo projeto).

    SÓ RODA SE has_consent() for True. Nenhuma chamada de rede acontece na
    importação do módulo nem na criação da instância — só dentro de sync(),
    e mesmo assim só depois de checar o consentimento.
    """

    def __init__(self, credentials_path: str = CREDENTIALS_PATH, kb_json_path: str = KB_JSON_PATH):
        self.credentials_path = credentials_path
        self.kb_json_path = kb_json_path
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        from google.cloud import firestore
        from google.oauth2 import service_account

        # Três formas de fornecer a credencial, nessa ordem — a primeira
        # que existir é usada:
        #
        # 1) FIREBASE_SERVICE_ACCOUNT_JSON — variável de ambiente com o
        #    CONTEÚDO do JSON (não o caminho). É o formato pra colar numa
        #    Secret do GitHub Actions/HuggingFace Spaces — a chave nunca
        #    toca o repositório.
        # 2) GOOGLE_APPLICATION_CREDENTIALS — variável de ambiente padrão
        #    do Google, apontando pro CAMINHO de um arquivo JSON no
        #    servidor (útil em VM/servidor próprio).
        # 3) O arquivo local (self.credentials_path) — conveniência pra
        #    rodar na sua máquina em desenvolvimento. Esse caminho tem que
        #    estar no .gitignore.
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
            cred_path = Path(self.credentials_path)
            if not cred_path.exists():
                raise FileNotFoundError(
                    f"Nenhuma credencial do Firebase encontrada. Rodando local: salva o JSON "
                    f"de service account em '{self.credentials_path}' (esse caminho tem que "
                    f"estar no .gitignore). Em produção/deploy (GitHub Actions, HuggingFace "
                    f"Spaces etc.): defina a variável de ambiente FIREBASE_SERVICE_ACCOUNT_JSON "
                    f"com o CONTEÚDO do JSON, ou GOOGLE_APPLICATION_CREDENTIALS apontando pro "
                    f"caminho do arquivo no servidor."
                )
            credentials = service_account.Credentials.from_service_account_file(str(cred_path))
            project_id = json.loads(cred_path.read_text(encoding="utf-8")).get("project_id")

        self._client = firestore.Client(project=project_id, credentials=credentials)
        return self._client

    async def sync(self, machine_id: str) -> int:
        """Roda em thread separada (I/O de rede/disco é bloqueante) e
        devolve quantos documentos foram enviados. Não faz nada (devolve 0)
        se o usuário não tiver dado consentimento."""
        if not has_consent():
            return 0
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_blocking, machine_id)

    def _sync_blocking(self, machine_id: str) -> int:
        kb_path = Path(self.kb_json_path)
        if not kb_path.exists():
            return 0

        with open(kb_path, "r", encoding="utf-8") as f:
            documents = json.load(f)
        if isinstance(documents, dict):
            documents = [documents]
        if not documents:
            return 0

        client = self._get_client()
        from google.cloud import firestore
        collection = (
            client.collection(FIRESTORE_ROOT_COLLECTION)
            .document(machine_id)
            .collection(FIRESTORE_SUBCOLLECTION)
        )

        sent = 0
        batch = client.batch()
        pending = 0
        for doc in documents:
            doc_id = doc.get("id")
            if not doc_id:
                continue
            batch.set(collection.document(doc_id), doc)
            sent += 1
            pending += 1
            if pending >= BATCH_SIZE:
                batch.commit()
                batch = client.batch()
                pending = 0
        if pending:
            batch.commit()

        client.collection(FIRESTORE_ROOT_COLLECTION).document(machine_id).set(
            {"last_synced_at": firestore.SERVER_TIMESTAMP, "document_count": sent},
            merge=True,
        )

        logger.info(f"FirestoreSync: {sent} documento(s) sincronizado(s) para a máquina {machine_id}.")
        return sent
