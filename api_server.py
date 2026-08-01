import os
import time
import platform
import threading
import webbrowser
import importlib
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel
from phoenix_kernel.kernel import PhoenixKernel
# Importa as funções de consentimento do nosso módulo de nuvem
from phoenix_kernel.cloud_sync import has_consent, grant_consent, revoke_consent

app = FastAPI(title="Phoenix Engine API", version="5.0.0")
kernel = PhoenixKernel()
app.start_time = time.monotonic()

LICENSE_PATH = "LICENSE.md"
LICENSE_ACCEPTED_FLAG = "data/license_accepted.flag"

# Importa o core de telemetria dinamicamente
hardware_core = importlib.import_module("phoenix_kernel.telemetry.core")

@app.on_event("startup")
async def startup_event():
    # O boot() do kernel já cuida de tudo agora: hardware, RAG, runtime,
    # E a Phoenix Aviary Platform (build + processo Node supervisionado
    # na porta 3000, com auto-restart). Ver kernel.py / platform_process.py.
    await kernel.boot()

@app.on_event("shutdown")
async def shutdown_event():
    await kernel.shutdown()

@app.get("/")
async def get_index():
    html_path = Path("web/index.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="web/index.html não encontrado")
    return FileResponse(html_path)

@app.get("/health")
async def health_check():
    """Endpoint de Health Check para o Bootstrapper."""
    return {
        "status": "healthy",
        "version": "5.0.0",
        "python": platform.python_version(),
        "engine": "Phoenix",
        "uptime": time.monotonic() - app.start_time
    }

# NOTA: a rota /platform (sub-rota estática na 8000) foi removida.
# A Phoenix Aviary Platform NÃO é um site estático - é um servidor
# Node.js próprio (platform_source/dist/server.cjs) com ping de
# provedores feito do lado do servidor. Ela roda na sua própria porta
# (3000), supervisionada pelo kernel (ver phoenix_kernel/07_services/
# platform_process.py). Acesse direto em http://localhost:3000.

@app.get("/api/state")
async def get_state():
    state_data = await kernel.state.get_state()
    if "error" in state_data:
        raise HTTPException(status_code=503, detail=state_data["error"])
    return state_data

@app.get("/api/hardware/all")
async def get_hardware_all():
    try:
        devices = hardware_core.get_all_hardware_sensors()
        return {"devices": devices}
    except Exception as e:
        return {"devices": [], "error": str(e)}

class CommandRequest(BaseModel):
    command: str

@app.post("/api/command")
async def handle_command(req: CommandRequest):
    return await kernel.api.process_command(req.command.strip())

@app.get("/api/missions")
async def get_missions():
    try:
        return list(kernel.services.packages.catalog.packages.values())
    except:
        return []

@app.get("/api/missions/{package_id}")
async def resolve_mission(package_id: str):
    try:
        resolved = await kernel.planner.resolve_package(package_id)
        if not resolved:
            raise HTTPException(status_code=404, detail="Missão não encontrada")
        return resolved
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class InstallReq(BaseModel):
    package_id: str

@app.post("/api/missions/install")
async def install_mission(req: InstallReq):
    try:
        result = await kernel.services.install_package(req.package_id)
        return {"output": result}
    except Exception as e:
        return {"output": str(e)}

# --- Ponte direta de geração de imagem (Opção B2 — sem passar pela aprovação
# de missão), usada pelo Chat WebUI da Phoenix Aviary Platform (porta 3000) ---

class GenerateImageReq(BaseModel):
    prompt: str
    model_hint: str = ""  # opcional: "flux", "sdxl", "sd15" — mesma heurística do Mission Executor

@app.post("/api/generate-image")
async def generate_image(req: GenerateImageReq):
    # ATENÇÃO (Claude): assumindo que o kernel expõe o ResidentManager como
    # `kernel.resident`, seguindo o mesmo padrão de kernel.services/planner/
    # state/cloud_sync já usados nos outros endpoints deste arquivo. Não
    # tenho o kernel.py pra confirmar o nome exato do atributo — se o boot()
    # guardar a instância em outro nome (ex: kernel.mission_kernel), troque
    # só essa linha abaixo.
    resident = getattr(kernel, "resident", None)
    if resident is None:
        raise HTTPException(
            status_code=503,
            detail="ResidentManager não encontrado em kernel.resident. Confira em kernel.py qual é o "
                   "atributo real onde o ResidentManager foi guardado durante o boot() e ajuste este endpoint."
        )
    try:
        result = await resident.generate_image_direct(req.prompt, req.model_hint)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado na ponte de imagem: {e}")

    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result.get("error", "Falha desconhecida ao gerar imagem."))

    # Lê o PNG gerado e devolve em base64 — evita ter que criar uma rota
    # estática nova só pra servir a pasta output/images/ pro Aviary (porta
    # 3000) buscar via fetch cross-origin.
    img_path = Path(result["path"])
    if not img_path.exists():
        raise HTTPException(status_code=500, detail=f"Driver reportou sucesso mas o arquivo não existe em disco: {img_path}")

    import base64
    with open(img_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("ascii")

    return {
        "ok": True,
        "model": result.get("model"),
        "path": str(img_path),
        "image_base64": image_b64,
        "mime_type": "image/png",
    }

@app.get("/api/license")
async def get_license():
    try:
        with open(LICENSE_PATH, "r", encoding="utf-8") as f:
            text = f.read()
    except:
        text = "License file not found."
    accepted = os.path.exists(LICENSE_ACCEPTED_FLAG)
    return {"text": text, "accepted": accepted}

@app.post("/api/license/accept")
async def accept_license():
    os.makedirs(os.path.dirname(LICENSE_ACCEPTED_FLAG), exist_ok=True)
    with open(LICENSE_ACCEPTED_FLAG, "w") as f:
        f.write("accepted")
    return {"ok": True}

# --- Endpoints de Telemetria e Firestore (100% Reais) ---

@app.get("/api/telemetry/consent")
async def get_telemetry_consent():
    return {"consent": has_consent()}

@app.post("/api/telemetry/consent/accept")
async def accept_telemetry_consent():
    grant_consent()
    # Força uma sincronização imediata ao aceitar
    try:
        await kernel.cloud_sync.sync_knowledge_base()
    except: pass
    return {"consent": True}

@app.post("/api/telemetry/consent/decline")
async def decline_telemetry_consent():
    revoke_consent()
    return {"consent": False}

@app.post("/api/telemetry/sync")
async def trigger_telemetry_sync():
    if not has_consent():
        return {"sent": 0, "consent": False, "error": "Consentimento não concedido."}
    try:
        # Sobe a base de conhecimento imediatamente
        sent = await kernel.cloud_sync.sync_knowledge_base()
        # Sobe o estado atual da máquina imediatamente
        state_data = await kernel.state.get_state()
        await kernel.cloud_sync.sync_machine_state(state_data)
        return {"sent": sent, "consent": True}
    except Exception as e:
        return {"sent": 0, "consent": True, "error": str(e)}

def open_browser():
    webbrowser.open_new("http://localhost:8000")

if __name__ == "__main__":
    import uvicorn
    print("\n[✓] Phoenix API rodando em http://localhost:8000")
    print("[✓] Phoenix Aviary Platform em http://localhost:3000")
    threading.Timer(1.5, open_browser).start()
    try:
        uvicorn.run(app, host="localhost", port=8000)
    except KeyboardInterrupt:
        print("\n[✓] Desligando Phoenix API...")