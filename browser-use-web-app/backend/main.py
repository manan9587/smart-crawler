import asyncio
import json
import uuid
import sys
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Fix Windows asyncio subprocess issue
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from backend.agent_manager import AgentManager
from backend.models import TaskRequest
from backend.utils import process_file, validate_api_key, setup_logging

logger = setup_logging()

app = FastAPI(title="Browser-Use Web Interface")

# Simple CORS setup without complex settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Static files - pointing to frontend directory
static_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Global agent manager
manager = AgentManager()

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    return FileResponse(static_dir / "index.html")

@app.post("/api/v1/agent/start")
async def start_agent(req: TaskRequest):
    """Start the browser automation agent"""
    try:
        # Validate API key
        if not validate_api_key(req.api_key, req.llm_provider):
            raise HTTPException(status_code=400, detail="Invalid API key")
        
        if manager.is_running():
            raise HTTPException(status_code=400, detail="Agent already running")
        
        # Start agent
        task_id = await manager.start_agent(req)
        return {"status": "started", "task_id": task_id}
    
    except Exception as e:
        logger.error(f"Error starting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/agent/pause")
async def pause_agent():
    """Pause the running agent"""
    if not manager.is_running():
        raise HTTPException(status_code=400, detail="Agent not running")
    
    await manager.pause_agent()
    return {"status": "paused"}

@app.post("/api/v1/agent/resume")
async def resume_agent():
    """Resume the paused agent"""
    if not manager.is_paused():
        raise HTTPException(status_code=400, detail="Agent not paused")
    
    await manager.resume_agent()
    return {"status": "resumed"}

@app.post("/api/v1/agent/stop")
async def stop_agent():
    """Stop the agent"""
    await manager.stop_agent()
    return {"status": "stopped"}

@app.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a file"""
    if file.size and file.size > 10_000_000:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    
    try:
        content = await process_file(file)
        return {"filename": file.filename, "content": content}
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")

@app.websocket("/ws/agent-stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time agent updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/api/v1/agent/status")
def get_agent_status():
    """Get current agent status"""
    return manager.get_status()

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8000, 
        reload=True,
        log_level="info"
    )