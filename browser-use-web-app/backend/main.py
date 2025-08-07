import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.agent_manager import AgentManager
from backend.models import TaskRequest
from backend.utils import process_file, validate_api_key, setup_logging

logger = setup_logging()
app = FastAPI(title="Browser-Use Web Interface")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
static_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

manager = AgentManager()

@app.get("/", response_class=HTMLResponse)
async def ui():
    return FileResponse(static_dir / "index.html")

@app.post("/api/v1/agent/start")
async def start_agent(req: TaskRequest):
    # Validate API key
    if not validate_api_key(req.api_key, req.llm_provider):
        raise HTTPException(400, "Invalid API key")
    if manager.is_running():
        raise HTTPException(400, "Agent already running")
    # Start in background
    task_id = await manager.start_agent(req)
    return {"status": "started", "task_id": task_id}

@app.post("/api/v1/agent/pause")
async def pause():
    if not manager.is_running():
        raise HTTPException(400, "Not running")
    await manager.pause_agent()
    return {"status": "paused"}

@app.post("/api/v1/agent/resume")
async def resume():
    if not manager.is_paused():
        raise HTTPException(400, "Not paused")
    await manager.resume_agent()
    return {"status": "resumed"}

@app.post("/api/v1/agent/stop")
async def stop():
    await manager.stop_agent()
    return {"status": "stopped"}

@app.post("/api/v1/upload")
async def upload(file: UploadFile = File(...)):
    if file.spool_max_size > 10_000_000:
        raise HTTPException(400, "File too large")
    content = await process_file(file)
    return {"filename": file.filename, "content": content}

@app.websocket("/ws/agent-stream")
async def ws(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(ws)

@app.get("/api/v1/agent/status")
def status():
    return manager.get_status()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
