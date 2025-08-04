import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Browser-Use Web Interface")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

class TaskRequest(BaseModel):
    task: str
    api_key: Optional[str] = None
    model: str = "gpt-4o"
    context: Optional[Dict[str, Any]] = None
    image: Optional[str] = None

class AgentState(BaseModel):
    status: str = "idle"
    current_url: Optional[str] = None
    steps_completed: int = 0
    start_time: Optional[datetime] = None
    results: List[Dict[str, Any]] = []

class AgentManager:
    def __init__(self):
        self.state = AgentState()
        self.ws_connections: List[WebSocket] = []
        self.task_id: Optional[str] = None

    async def broadcast(self, data: Dict):
        text = json.dumps(data)
        for ws in list(self.ws_connections):
            try:
                await ws.send_text(text)
            except:
                self.ws_connections.remove(ws)

    async def start(self, req: TaskRequest):
        self.task_id = str(uuid.uuid4())
        self.state = AgentState(status="running", start_time=datetime.now())
        await self.broadcast({"type":"status", "status":"running", "task_id":self.task_id})
        await self.simulate(req)

    async def simulate(self, req: TaskRequest):
        steps = [
            "Initializing agent...",
            "Starting browser...",
            "Navigating to site...",
            "Extracting data...",
            "Compiling results...",
            "Done!"
        ]
        sample = [
            {"item":"MacBook Air M2", "description":"13\" M2", "price":"$999", "url":"https://apple.com/macbook-air"},
            {"item":"Dell XPS 13", "description":"Intel i7", "price":"$899", "url":"https://dell.com/xps-13"}
        ]
        for i, msg in enumerate(steps):
            await asyncio.sleep(2)
            self.state.steps_completed = i + 1
            if i < len(sample):
                self.state.results.append(sample[i])
            await self.broadcast({
                "type":"step",
                "message": msg,
                "url": f"https://step{i+1}.example",
                "results": self.state.results,
                "screenshot": "data:image/png;base64,PLACEHOLDER"
            })
        self.state.status = "completed"
        await self.broadcast({"type":"status", "status":"completed", "final": self.state.results})

    async def pause(self):
        self.state.status = "paused"
        await self.broadcast({"type":"status","status":"paused"})

    async def resume(self):
        self.state.status = "running"
        await self.broadcast({"type":"status","status":"running"})

    async def stop(self):
        self.state.status = "idle"
        await self.broadcast({"type":"status","status":"idle"})

manager = AgentManager()

@app.get("/", response_class=FileResponse)
def root():
    return "static/index.html"

@app.post("/api/v1/agent/start")
async def start(req: TaskRequest):
    if manager.state.status == "running":
        raise HTTPException(400, "Agent already running")
    if req.image:
        req.context = req.context or {}
        req.context["image"] = req.image
    asyncio.create_task(manager.start(req))
    return {"status": "started", "task_id": manager.task_id}

@app.post("/api/v1/agent/pause")
async def pause():
    if manager.state.status != "running":
        raise HTTPException(400, "Not running")
    await manager.pause()
    return {"status": "paused"}

@app.post("/api/v1/agent/resume")
async def resume():
    if manager.state.status != "paused":
        raise HTTPException(400, "Not paused")
    await manager.resume()
    return {"status": "resumed"}

@app.post("/api/v1/agent/stop")
async def stop():
    await manager.stop()
    return {"status": "stopped"}

@app.post("/api/v1/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    text = data.decode() if "text" in file.content_type else f"Binary {file.filename}"
    return {"filename": file.filename, "text_content": text[:500]}

@app.websocket("/ws/agent-stream")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    manager.ws_connections.append(ws)
    await ws.send_text(json.dumps({"type": "connected", "status": manager.state.status}))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.ws_connections.remove(ws)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
