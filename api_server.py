import os
import platform
import threading
import webbrowser
import importlib
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel

from phoenix_kernel.kernel import PhoenixKernel
from phoenix_kernel import cloud_sync

# core.py mora em phoenix_kernel/06_telemetry/core.py. "06_telemetry" começa
# com dígito, não dá pra fazer "from phoenix_kernel.06_telemetry import
# core" direto (SyntaxError) — por isso importlib.
hardware_core = importlib.import_module("phoenix_kernel.06_telemetry.core")

app = FastAPI(title="Phoenix Engine API", version="5.0.0")
kernel = PhoenixKernel()

LICENSE_PATH = "LICENSE.md"
LICENSE_ACCEPTED_FLAG = "data/license_accepted.flag"

@app.on_event("startup")
async def startup_event():
    await kernel.boot()

@app.on_event("shutdown")
async def shutdown_event():
    await kernel.shutdown()

@app.get("/")
async def get_index():
    return FileResponse("web/index.html")

@app.get("/api/state")
async def get_state():
    state_data = await kernel.state.get_state()
    if "error" in state_data: raise HTTPException(status_code=503, detail=state_data["error"])
    return state_data

@app.get("/api/hardware/all")
async def get_hardware_all():
    """
    Todos os dispositivos de hardware com todos os sensores — via
    06_telemetry/core.py, a MESMA fonte que a telemetria ao vivo já usa.
    Antes existiam DUAS implementações desse scanner (uma aqui dentro do
    api_server.py, outra em core.py) — cada uma podia ficar desatualizada
    sem a outra saber. Agora só existe uma, e este endpoint só chama ela.
    """
    try:
        devices = hardware_core.get_all_hardware_sensors()
        return {
            "devices": devices,
            "diagnostic": {"system": platform.system(), "devices_with_sensors": len(devices), "error": None},
        }
    except Exception as e:
        return {
            "devices": [],
            "diagnostic": {"system": platform.system(), "devices_with_sensors": 0, "error": f"{type(e).__name__}: {e}"},
        }

class CommandRequest(BaseModel):
    command: str

@app.post("/api/command")
async def handle_command(req: CommandRequest):
    return await kernel.api.process_command(req.command.strip())

@app.get("/api/missions")
async def get_missions():
    return list(kernel.services.packages.catalog.packages.values())

@app.get("/api/missions/{package_id}")
async def resolve_mission(package_id: str):
    resolved = await kernel.planner.resolve_package(package_id)
    if not resolved: raise HTTPException(status_code=404, detail="Missão não encontrada")
    return resolved

class InstallReq(BaseModel):
    package_id: str

@app.post("/api/missions/install")
async def install_mission(req: InstallReq):
    result = await kernel.services.install_package(req.package_id)
    return {"output": result}

@app.get("/api/license")
async def get_license():
    try:
        with open(LICENSE_PATH, "r", encoding="utf-8") as f: text = f.read()
    except: text = "License file not found."
    accepted = os.path.exists(LICENSE_ACCEPTED_FLAG)
    return {"text": text, "accepted": accepted}

@app.post("/api/license/accept")
async def accept_license():
    os.makedirs(os.path.dirname(LICENSE_ACCEPTED_FLAG), exist_ok=True)
    with open(LICENSE_ACCEPTED_FLAG, "w") as f: f.write("accepted")
    return {"ok": True}

@app.get("/api/telemetry/consent")
async def get_telemetry_consent():
    """Estado atual do consentimento pra sincronizar o RAG local (benchmarks,
    hardware, eventos de telemetria) com o Firestore."""
    return {"consent": cloud_sync.has_consent()}

@app.post("/api/telemetry/consent/accept")
async def accept_telemetry_consent():
    cloud_sync.grant_consent()
    return {"consent": True}

@app.post("/api/telemetry/consent/decline")
async def decline_telemetry_consent():
    cloud_sync.revoke_consent()
    return {"consent": False}

@app.post("/api/telemetry/sync")
async def trigger_telemetry_sync():
    """Sincronização manual com o Firestore agora, sem esperar o loop
    automático. Só faz algo de fato se já houver consentimento."""
    if kernel.cloud_sync is None:
        raise HTTPException(status_code=501, detail="google-cloud-firestore não está instalado neste ambiente.")
    try:
        machine_id = cloud_sync.get_or_create_machine_id()
        sent = await kernel.cloud_sync.sync(machine_id)
        return {"sent": sent, "consent": cloud_sync.has_consent()}
    except FileNotFoundError as e:
        raise HTTPException(status_code=412, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"falha ao sincronizar com o Firestore: {e}")

def open_browser():
    webbrowser.open_new("http://localhost:8000")

if __name__ == "__main__":
    import uvicorn
    print("\n[✓] Phoenix API rodando em http://localhost:8000")
    threading.Timer(1.5, open_browser).start()
    try:
        uvicorn.run(app, host="localhost", port=8000)
    except KeyboardInterrupt:
        print("\n[Shutdown] Servidor interrompido pelo usuário (Ctrl+C).")
