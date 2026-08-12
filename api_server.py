# api_server.py

import os
import time
import platform
import threading
import webbrowser
import importlib
import base64
import uuid
import shutil
from fastapi import FastAPI
from fastapi import UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel
from phoenix_kernel.kernel import PhoenixKernel
# Importa as funções de consentimento do nosso módulo de nuvem
from phoenix_kernel.cloud_sync import has_consent, grant_consent, revoke_consent
from core.domain.execution import ExecutionPlan, ExecutionStatus

app = FastAPI(title="Phoenix Engine API", version="5.1.0") # Versão bumped para Document Engine
kernel = PhoenixKernel()
app.start_time = time.monotonic()

LICENSE_PATH = "LICENSE.md"
LICENSE_ACCEPTED_FLAG = "data/license_accepted.flag"

# Importa o core de telemetria dinamicamente
hardware_core = importlib.import_module("phoenix_kernel.telemetry.core")

@app.on_event("startup")
async def startup_event():
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
        "version": "5.1.0",
        "python": platform.python_version(),
        "engine": "Phoenix",
        "uptime": time.monotonic() - app.start_time
    }

@app.get("/api/state")
async def get_state():
    state_data = await kernel.state.get_state()
    if "error" in state_data:
        raise HTTPException(status_code=503, detail=state_data["error"])
    return state_data

@app.get("/api/chat/pending")
async def get_pending_chat_messages():
    messages = kernel.resident.pending_chat_messages
    kernel.resident.pending_chat_messages = []
    return {"messages": messages}

@app.get("/api/hardware/all")
async def get_hardware_all():
    try:
        devices = hardware_core.get_all_hardware_sensors()
        return {"devices": devices}
    except Exception as e:
        return {"devices": [], "error": str(e)}

class CommandRequest(BaseModel):
    command: str

@app.post("/api/describe-image")
async def describe_image(file: UploadFile = File(...), prompt: str = Form("Descreva esta imagem")):
    """Recebe uma imagem, salva temporariamente e usa o llama-mtmd-cli (MiniCPM-V) para descreve-la."""
    _ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}
    _raw_name = (file.filename or "upload").strip()
    _safe_ext = Path(_raw_name).suffix.lower()
    if _safe_ext not in _ALLOWED_IMAGE_EXTS:
        _safe_ext = ".bin"
    _safe_filename = f"{uuid.uuid4()}{_safe_ext}"

    temp_dir = Path("temp/vision")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / _safe_filename

    try:
        with temp_file.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # PHX-NEW (Fase 2): "minicpmv" hardcoded virou resolução por
        # capacidade via o Model Registry do ResidentManager. Se por
        # algum motivo o registry não resolver a role "vision" (catálogo
        # ausente/corrompido), cai pro literal antigo como rede de
        # segurança - o endpoint nunca quebra por causa do catálogo.
        resident = getattr(kernel, "resident", None)
        resolved_vision = resident.registry.resolve("vision") if resident else None
        vision_runtime = resolved_vision.runtime if resolved_vision else "vision"
        vision_model = resolved_vision.id if resolved_vision else "minicpmv"

        plan = ExecutionPlan(
            runtime=vision_runtime,
            model=vision_model,
            parameters={
                "image_path": str(temp_file.resolve()), 
                "prompt": prompt
            },
            reasoning="Analise de imagem via MiniCPM-V",
        )

        result = await kernel.runtime.execute(plan)

        if result.status == ExecutionStatus.SUCCESS:
            return {"text": result.output}
        return {"error": result.errors[0] if result.errors else "Erro desconhecido na analise"}

    except Exception as e:
        return {"error": str(e)}
    finally:
        if temp_file.exists():
            temp_file.unlink()


class SynthesizeSpeechReq(BaseModel):
    text: str
    voice: str = ""
    length_scale: float | None = None

@app.post("/api/synthesize-speech")
async def synthesize_speech(req: SynthesizeSpeechReq):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Campo 'text' vazio - nada para sintetizar.")

    parameters = {"text": text}
    if req.length_scale is not None:
        parameters["length_scale"] = req.length_scale

    plan = ExecutionPlan(
        runtime="piper",
        model=req.voice,
        parameters=parameters,
        reasoning="Síntese de voz neural local via Piper",
    )

    try:
        result = await kernel.runtime.execute(plan)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado na ponte de TTS: {e}")

    if result.status != ExecutionStatus.SUCCESS:
        raise HTTPException(
            status_code=422,
            detail=result.errors[0] if result.errors else "Falha desconhecida ao sintetizar voz.",
        )

    output_str = str(result.output or "")
    audio_path = Path(output_str.split("Audio salvo em:", 1)[-1].strip()) if "Audio salvo em:" in output_str else None
    if not audio_path or not audio_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"PiperDriver reportou sucesso mas o arquivo de áudio não foi encontrado ({audio_path}).",
        )

    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("ascii")

    return {
        "ok": True,
        "voice": req.voice or "pt_BR-faber-medium",
        "path": str(audio_path),
        "audio_base64": audio_b64,
        "mime_type": "audio/wav",
    }

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

class GenerateImageReq(BaseModel):
    prompt: str
    model_hint: str = ""

@app.post("/api/generate-image")
async def generate_image(req: GenerateImageReq):
    resident = getattr(kernel, "resident", None)
    if resident is None:
        raise HTTPException(status_code=503, detail="ResidentManager não encontrado.")
    try:
        result = await resident.generate_image_direct(req.prompt, req.model_hint)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado na ponte de imagem: {e}")

    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result.get("error", "Falha desconhecida ao gerar imagem."))

    img_path = Path(result["path"])
    if not img_path.exists():
        raise HTTPException(status_code=500, detail=f"Driver reportou sucesso mas o arquivo não existe em disco: {img_path}")

    with open(img_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("ascii")

    return {
        "ok": True,
        "model": result.get("model"),
        "path": str(img_path),
        "image_base64": image_b64,
        "mime_type": "image/png",
    }

# ==========================================
# DOCUMENT ENGINE (PyMuPDF + LLM Analysis)
# ==========================================
@app.post("/api/documents/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """Recebe um documento (PDF/DOCX), extrai o texto usando PyMuPDF e envia para o Qwen analisar."""
    temp_dir = Path("temp/documents")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / f"{uuid.uuid4()}_{file.filename}"
    
    try:
        with temp_file.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        extracted_text = ""
        
        # Tenta usar PyMuPDF4LLM para PDFs (Extração estruturada em Markdown)
        if temp_file.suffix.lower() == ".pdf":
            try:
                import pymupdf4llm
                extracted_text = pymupdf4llm.to_markdown(str(temp_file))
            except ImportError:
                import fitz # Fallback para PyMuPDF padrão
                doc = fitz.open(str(temp_file))
                for page in doc:
                    extracted_text += page.get_text()
        else:
            # Placeholder para Apache Tika (futuro) ou leitura direta de TXT
            try:
                extracted_text = temp_file.read_text(encoding="utf-8")
            except:
                pass
                
        if not extracted_text:
            return {"error": "Não foi possível extrair texto do documento."}

        # Limita o tamanho do texto para não estourar o contexto do LLM (ex: 6000 chars)
        text_chunk = extracted_text[:6000]

        plan = ExecutionPlan(
            runtime="llama.cpp",
            model="qwen3:8b",
            parameters={
                "system_prompt": "Você é o Phoenix Document Engine. Analise o documento fornecido, extraia os pontos principais e formate a saída em Markdown.",
                "user_prompt": f"Analise o seguinte documento:\n\n{text_chunk}"
            }
        )
        
        result = await kernel.runtime.execute(plan)

        if result.status == ExecutionStatus.SUCCESS:
            return {"text": result.output, "extracted_length": len(extracted_text)}
        return {"error": result.errors[0] if result.errors else "Erro ao processar com LLM"}

    except Exception as e:
        return {"error": str(e)}
    finally:
        if temp_file.exists():
            temp_file.unlink()

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

# --- Endpoints de Telemetria e Firestore ---

@app.get("/api/telemetry/consent")
async def get_telemetry_consent():
    return {"consent": has_consent()}

@app.post("/api/telemetry/consent/accept")
async def accept_telemetry_consent():
    grant_consent()
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
        sent = await kernel.cloud_sync.sync_knowledge_base()
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