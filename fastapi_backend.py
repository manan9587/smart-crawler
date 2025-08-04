import asyncio
import json
import uuid
import base64
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Browser-Use imports
try:
    from browser_use import Agent
    from browser_use.browser import BrowserSession
    from langchain_openai import ChatOpenAI
    from langchain_google_genai import ChatGoogleGenerativeAI
    BROWSER_USE_AVAILABLE = True
except ImportError:
    print("Warning: browser-use not installed. Install with: pip install browser-use langchain-google-genai")
    BROWSER_USE_AVAILABLE = False

load_dotenv()

app = FastAPI(title="Browser-Use Web Interface")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

class TaskRequest(BaseModel):
    task: str
    api_key: Optional[str] = None
    model: str = os.getenv('DEFAULT_MODEL', 'gemini-pro')
    context: Optional[Dict[str, Any]] = None
    image: Optional[str] = None

class AgentState(BaseModel):
    status: str = "idle"
    current_url: Optional[str] = None
    steps_completed: int = 0
    start_time: Optional[datetime] = None
    results: List[Dict[str, Any]] = []
    paused: bool = False

class AgentManager:
    def __init__(self):
        self.state = AgentState()
        self.ws_connections: List[WebSocket] = []
        self.task_id: Optional[str] = None
        self.agent: Optional[Agent] = None
        self.browser_session: Optional[BrowserSession] = None
        self.pause_requested = False
        self.stop_requested = False

    async def broadcast(self, data: Dict):
        """Send data to all connected WebSocket clients"""
        text = json.dumps(data)
        disconnected = []
        for ws in self.ws_connections:
            try:
                await ws.send_text(text)
            except:
                disconnected.append(ws)
        # Remove disconnected clients
        for ws in disconnected:
            self.ws_connections.remove(ws)

    async def start(self, req: TaskRequest):
        """Start the Browser-Use agent"""
        self.task_id = str(uuid.uuid4())
        self.state = AgentState(status="running", start_time=datetime.now())
        self.pause_requested = False
        self.stop_requested = False
        
        await self.broadcast({
            "type": "status",
            "status": "running",
            "task_id": self.task_id
        })
        
        if BROWSER_USE_AVAILABLE:
            await self.run_browser_use_agent(req)
        else:
            await self.simulate(req)

    async def run_browser_use_agent(self, req: TaskRequest):
        """Run actual Browser-Use agent"""
        try:
            # Determine which API to use based on model
            if req.model.startswith('gemini'):
                # Use Gemini
                api_key = req.api_key or os.getenv('GOOGLE_API_KEY')
                if not api_key:
                    await self.broadcast({
                        "type": "error",
                        "message": "Google/Gemini API key required. Set GOOGLE_API_KEY in .env file or provide in request."
                    })
                    self.state.status = "idle"
                    await self.broadcast({"type": "status", "status": "idle"})
                    return
                
                # Initialize Gemini LLM
                llm = ChatGoogleGenerativeAI(
                    model=req.model,
                    google_api_key=api_key,
                    temperature=0.7
                )
                await self.broadcast({
                    "type": "step",
                    "message": f"Using Gemini model: {req.model}"
                })
            else:
                # Use OpenAI
                api_key = req.api_key or os.getenv('OPENAI_API_KEY')
                if not api_key:
                    await self.broadcast({
                        "type": "error",
                        "message": "OpenAI API key required. Set OPENAI_API_KEY in .env file or provide in request."
                    })
                    self.state.status = "idle"
                    await self.broadcast({"type": "status", "status": "idle"})
                    return
                
                # Initialize OpenAI LLM
                llm = ChatOpenAI(
                    model=req.model,
                    openai_api_key=api_key,
                    temperature=0.7
                )
                await self.broadcast({
                    "type": "step",
                    "message": f"Using OpenAI model: {req.model}"
                })
            
            # Prepare context
            context = req.context or {}
            if req.image:
                context["image"] = req.image
            
            # Initialize Browser-Use agent
            self.agent = Agent(
                task=req.task,
                llm=llm,
                browser=BrowserSession(headless=True),  # Set to False to see browser
                max_steps=50
            )
            
            # Run agent with hooks
            await self.agent.run(
                on_step_start=self.on_step_start,
                on_step_end=self.on_step_end
            )
            
            self.state.status = "completed"
            await self.broadcast({
                "type": "status",
                "status": "completed",
                "final_results": self.state.results
            })
            
        except Exception as e:
            error_msg = f"Agent error: {str(e)}"
            await self.broadcast({
                "type": "error",
                "message": error_msg
            })
            self.state.status = "idle"
            await self.broadcast({"type": "status", "status": "idle"})

    async def on_step_start(self, step_info: Dict):
        """Called when agent starts a step"""
        if self.stop_requested:
            raise Exception("Agent stopped by user")
        
        if self.pause_requested:
            await self.broadcast({
                "type": "status",
                "status": "paused"
            })
            while self.pause_requested and not self.stop_requested:
                await asyncio.sleep(0.5)
            if not self.stop_requested:
                await self.broadcast({
                    "type": "status",
                    "status": "running"
                })

    async def on_step_end(self, step_info: Dict):
        """Called when agent completes a step"""
        self.state.steps_completed += 1
        
        # Extract information from step
        action = step_info.get('action', 'Unknown action')
        url = step_info.get('url', '')
        
        # Try to get screenshot
        screenshot_data = None
        if hasattr(self.agent, 'browser_session'):
            try:
                # Get current page
                page = await self.agent.browser_session.get_current_page()
                if page:
                    # Take screenshot
                    screenshot = await page.screenshot(full_page=False)
                    screenshot_data = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                    
                    # Get current URL
                    url = page.url
            except Exception as e:
                print(f"Screenshot error: {e}")
        
        # Extract any data found
        extracted = step_info.get('extracted_content', {})
        if extracted:
            self.state.results.append(extracted)
        
        # Broadcast step update
        await self.broadcast({
            "type": "step",
            "message": f"Step {self.state.steps_completed}: {action}",
            "url": url,
            "screenshot": screenshot_data,
            "results": self.state.results,
            "step_info": step_info
        })

    async def simulate(self, req: TaskRequest):
        """Fallback simulation when Browser-Use not available"""
        steps = [
            "Initializing browser automation...",
            f"Processing task: {req.task}",
            "Navigating to target website...",
            "Analyzing page content...",
            "Extracting relevant data...",
            "Compiling results..."
        ]
        
        # Simulate steps
        for i, msg in enumerate(steps):
            if self.stop_requested:
                break
                
            if self.pause_requested:
                self.state.status = "paused"
                await self.broadcast({"type": "status", "status": "paused"})
                while self.pause_requested and not self.stop_requested:
                    await asyncio.sleep(0.5)
                if not self.stop_requested:
                    self.state.status = "running"
                    await self.broadcast({"type": "status", "status": "running"})
            
            await asyncio.sleep(2)
            self.state.steps_completed = i + 1
            
            await self.broadcast({
                "type": "step",
                "message": msg,
                "url": f"https://example.com/step/{i+1}",
                "screenshot": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                "results": self.state.results
            })
        
        if not self.stop_requested:
            self.state.status = "completed"
            await self.broadcast({
                "type": "status",
                "status": "completed",
                "message": "Simulation completed. Install browser-use for real automation."
            })
        else:
            self.state.status = "idle"
            await self.broadcast({"type": "status", "status": "idle"})

    async def pause(self):
        """Pause the agent"""
        self.pause_requested = True
        self.state.paused = True
        self.state.status = "paused"
        await self.broadcast({"type": "status", "status": "paused"})

    async def resume(self):
        """Resume the agent"""
        self.pause_requested = False
        self.state.paused = False
        self.state.status = "running"
        await self.broadcast({"type": "status", "status": "running"})

    async def stop(self):
        """Stop the agent"""
        self.stop_requested = True
        self.pause_requested = False
        self.state = AgentState()  # Reset state
        await self.broadcast({"type": "status", "status": "idle"})

# Create global manager instance
manager = AgentManager()

@app.get("/", response_class=FileResponse)
async def root():
    return "static/index.html"

@app.post("/api/v1/agent/start")
async def start_agent(req: TaskRequest):
    if manager.state.status == "running":
        raise HTTPException(400, "Agent already running")
    
    # Start agent in background
    asyncio.create_task(manager.start(req))
    return {"status": "started", "task_id": manager.task_id}

@app.post("/api/v1/agent/pause")
async def pause_agent():
    if manager.state.status != "running":
        raise HTTPException(400, "Agent not running")
    await manager.pause()
    return {"status": "paused"}

@app.post("/api/v1/agent/resume")
async def resume_agent():
    if manager.state.status != "paused":
        raise HTTPException(400, "Agent not paused")
    await manager.resume()
    return {"status": "resumed"}

@app.post("/api/v1/agent/stop")
async def stop_agent():
    await manager.stop()
    return {"status": "stopped"}

@app.get("/api/v1/agent/status")
async def get_status():
    return {
        "status": manager.state.status,
        "steps_completed": manager.state.steps_completed,
        "results_count": len(manager.state.results)
    }

@app.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)):
    """Handle file uploads"""
    content = await file.read()
    
    # Process text files
    if file.content_type and "text" in file.content_type:
        text_content = content.decode('utf-8', errors='ignore')
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "text_content": text_content[:1000] + "..." if len(text_content) > 1000 else text_content
        }
    
    # For binary files, return basic info
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content),
        "text_content": f"Binary file: {file.filename}"
    }

@app.websocket("/ws/agent-stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    manager.ws_connections.append(websocket)
    
    # Send initial status
    await websocket.send_text(json.dumps({
        "type": "connected",
        "status": manager.state.status
    }))
    
    try:
        # Keep connection alive
        while True:
            # Wait for any message from client (ping/pong)
            data = await websocket.receive_text()
            # Could handle client commands here if needed
    except WebSocketDisconnect:
        manager.ws_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    print("Starting Browser-Use Web Interface...")
    print(f"Browser-Use available: {BROWSER_USE_AVAILABLE}")
    if not BROWSER_USE_AVAILABLE:
        print("Install browser-use for real automation: pip install browser-use langchain-google-genai")
    
    # Check for API keys
    openai_key = os.getenv('OPENAI_API_KEY', '').startswith('sk-')
    gemini_key = os.getenv('GOOGLE_API_KEY', '') != '' and os.getenv('GOOGLE_API_KEY', '') != 'your_gemini_api_key_here'
    
    print("\nAPI Keys Status:")
    print(f"- OpenAI API Key: {'✓ Configured' if openai_key else '✗ Not configured'}")
    print(f"- Gemini API Key: {'✓ Configured' if gemini_key else '✗ Not configured'}")
    print(f"- Default Model: {os.getenv('DEFAULT_MODEL', 'gemini-pro')}")
    
    if not openai_key and not gemini_key:
        print("\n⚠️  WARNING: No API keys configured! Add at least one to your .env file.")
    
    print(f"\nServer starting at http://127.0.0.1:{os.getenv('PORT', 8000)}")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv('PORT', 8000)))