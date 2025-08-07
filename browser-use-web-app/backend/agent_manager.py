import asyncio
import base64
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
from fastapi import WebSocket
from playwright.async_api import async_playwright

from backend.models import TaskRequest, AgentState
from backend.utils import get_llm_instance

class AgentManager:
    def __init__(self):
        self.state = AgentState()
        self.ws_conns: List[WebSocket] = []
        self.results: List[Dict[str, Any]] = []
        self.task_id = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.ws_conns.append(ws)
        await ws.send_text(json.dumps({"type": "connected", "status": self.state.status}))

    def disconnect(self, ws: WebSocket):
        if ws in self.ws_conns:
            self.ws_conns.remove(ws)

    async def broadcast(self, data: Dict[str, Any]):
        msg = json.dumps(data, default=str)
        for ws in list(self.ws_conns):
            try:
                await ws.send_text(msg)
            except:
                self.disconnect(ws)

    def is_running(self):
        return self.state.status == "running"

    def is_paused(self):
        return self.state.status == "paused"

    async def start_agent(self, req: TaskRequest):
        self.task_id = str(uuid.uuid4())
        self.state.status = "running"
        asyncio.create_task(self._run(req))
        return self.task_id

    async def _run(self, req: TaskRequest):
        await self.broadcast({"type": "status", "status": "running"})
        if req.headless is False:
            await self._run_real(req)
        else:
            await self._run_simulation(req)

    async def _run_real(self, req: TaskRequest):
        self.state.current_action = "Starting browser"
        await self.broadcast({"type": "step", "message": self.state.current_action})
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # LLM instance
        llm = get_llm_instance(req.llm_provider, req.api_key, req.model)
        # Example: navigate URL and fill form
        await page.goto(req.context.get("url", "about:blank"))
        await self.broadcast({"type": "step", "message": f"Navigated to {page.url}"})

        # Interpret simple form-filling instructions from prompt
        instructions = req.task.split(";")
        for instr in instructions:
            instr = instr.strip()
            if instr.lower().startswith("enter"):
                # Format: Enter "value" into the "fieldName" field
                import re
                m = re.match(r'Enter "(.*)" into the "(.*)" field', instr, re.IGNORECASE)
                if m:
                    val, field = m.groups()
                    selector = f'input[name="{field}"],input[id="{field}"]'
                    await page.fill(selector, val)
                    await self.broadcast({"type": "step", "message": f'Filled {field} with "{val}"'})
            elif instr.lower().startswith("click"):
                # Format: Click the "ButtonText" button
                import re
                m = re.match(r'Click the "(.*)" button', instr, re.IGNORECASE)
                if m:
                    btn = m.group(1)
                    await page.click(f'button:has-text("{btn}")')
                    await self.broadcast({"type": "step", "message": f'Clicked "{btn}" button'})
            # Take screenshot
            screenshot = await page.screenshot()
            b64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
            await self.broadcast({"type": "screenshot", "data": b64})

        await browser.close()
        await playwright.stop()
        self.state.status = "completed"
        await self.broadcast({"type": "status", "status": "completed"})

    async def _run_simulation(self, req: TaskRequest):
        for step in ["Init", "Start Browser", "Navigate", "Extract", "Done"]:
            await asyncio.sleep(1)
            await self.broadcast({"type": "step", "message": step})
        self.state.status = "completed"
        await self.broadcast({"type": "status", "status": "completed"})

    async def pause_agent(self):
        self.state.status = "paused"
        await self.broadcast({"type": "status", "status": "paused"})

    async def resume_agent(self):
        self.state.status = "running"
        await self.broadcast({"type": "status", "status": "running"})

    async def stop_agent(self):
        self.state.status = "idle"
        await self.broadcast({"type": "status", "status": "idle"})

    def get_status(self):
        return {"status": self.state.status, "steps_completed": self.state.steps_completed}
