import asyncio
import base64
import json
import uuid
import sys
import re
import subprocess
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import WebSocket

# Import for sync Playwright as workaround for Windows Python 3.13
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from backend.models import TaskRequest, AgentState
from backend.utils import get_llm_instance, setup_logging

logger = setup_logging()

class AgentManager:
    def __init__(self):
        self.state = AgentState()
        self.ws_connections: List[WebSocket] = []
        self.results: List[Dict[str, Any]] = []
        self.task_id: Optional[str] = None
        self.browser = None
        self.page = None
        self.playwright_instance = None
        self.is_paused_flag = False

    async def connect(self, websocket: WebSocket):
        """Connect a new WebSocket client"""
        await websocket.accept()
        self.ws_connections.append(websocket)
        await self._broadcast({
            "type": "connected", 
            "status": self.state.status,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"WebSocket connected. Total connections: {len(self.ws_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client"""
        if websocket in self.ws_connections:
            self.ws_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.ws_connections)}")

    async def _broadcast(self, data: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients"""
        if not self.ws_connections:
            return
        
        message = json.dumps(data, default=str)
        disconnected = []
        
        for ws in self.ws_connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(ws)
        
        # Remove disconnected clients
        for ws in disconnected:
            self.disconnect(ws)

    def is_running(self) -> bool:
        return self.state.status == "running"

    def is_paused(self) -> bool:
        return self.state.status == "paused"

    async def start_agent(self, req: TaskRequest) -> str:
        """Start the browser automation agent"""
        self.task_id = str(uuid.uuid4())
        self.state.status = "running"
        self.state.start_time = datetime.now()
        self.state.steps_completed = 0
        self.is_paused_flag = False
        
        # Start the agent task in background
        asyncio.create_task(self._run_agent(req))
        return self.task_id

    async def _run_agent(self, req: TaskRequest):
        """Main agent execution logic with Windows Python 3.13 workaround"""
        try:
            await self._broadcast({
                "type": "status", 
                "status": "running",
                "message": "Starting browser automation agent..."
            })
            
            # Use sync Playwright in a thread to avoid asyncio subprocess issues
            await self._run_sync_browser_task(req)
            
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            await self._broadcast({
                "type": "error",
                "message": f"Agent error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            self.state.status = "error"
        finally:
            await self._cleanup()

    async def _run_sync_browser_task(self, req: TaskRequest):
        """Run browser task using sync Playwright in executor to avoid asyncio issues"""
        
        if not PLAYWRIGHT_AVAILABLE:
            await self._run_simulation_mode(req)
            return
        
        # Run the sync browser automation in a thread executor
        loop = asyncio.get_event_loop()
        
        try:
            await loop.run_in_executor(None, self._sync_browser_automation, req)
        except Exception as e:
            logger.error(f"Browser automation error: {e}")
            # Fallback to simulation mode
            await self._run_simulation_mode(req)

    def _sync_browser_automation(self, req: TaskRequest):
        """Synchronous browser automation using sync Playwright"""
        try:
            # Use sync Playwright to avoid asyncio subprocess issues
            with sync_playwright() as playwright:
                # Launch browser
                browser = playwright.chromium.launch(
                    headless=True,  # Keep headless for stability
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage', 
                        '--disable-web-security'
                    ]
                )
                
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720}
                )
                page = context.new_page()
                
                # Send initial status
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": "step",
                        "message": "Browser started successfully",
                        "action": "Browser ready"
                    }),
                    asyncio.get_event_loop()
                )
                
                # Navigate to URL
                url = req.context.get("url", "about:blank")
                if url and url != "about:blank":
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(2)  # Wait for page to fully load
                    
                    # Take screenshot
                    screenshot = page.screenshot()
                    screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
                    
                    asyncio.run_coroutine_threadsafe(
                        self._broadcast({
                            "type": "screenshot",
                            "data": f"data:image/png;base64,{screenshot_b64}",
                            "description": f"Navigated to {url}"
                        }),
                        asyncio.get_event_loop()
                    )
                    
                    asyncio.run_coroutine_threadsafe(
                        self._broadcast({
                            "type": "step",
                            "message": f"Navigated to {url}",
                            "action": f"Navigate to {url}"
                        }),
                        asyncio.get_event_loop()
                    )
                
                # Parse and execute task instructions
                instructions = self._parse_instructions(req.task)
                
                for i, instruction in enumerate(instructions):
                    if self.is_paused_flag:
                        while self.is_paused_flag and self.state.status == "paused":
                            time.sleep(0.5)
                    
                    self._execute_sync_instruction(page, instruction, i + 1)
                    time.sleep(1.5)  # Longer delay between actions
                
                # Final screenshot
                screenshot = page.screenshot()
                screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
                
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": "screenshot",
                        "data": f"data:image/png;base64,{screenshot_b64}",
                        "description": "Task completed"
                    }),
                    asyncio.get_event_loop()
                )
                
                browser.close()
                
                # Mark as completed
                self.state.status = "completed"
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": "status",
                        "status": "completed", 
                        "message": "Task completed successfully"
                    }),
                    asyncio.get_event_loop()
                )
                
        except Exception as e:
            logger.error(f"Sync browser error: {e}")
            asyncio.run_coroutine_threadsafe(
                self._broadcast({
                    "type": "error",
                    "message": f"Browser error: {str(e)}"
                }),
                asyncio.get_event_loop()
            )
            raise

    def _execute_sync_instruction(self, page, instruction: Dict[str, str], step_num: int):
        """Execute a single instruction synchronously"""
        action = instruction["action"]
        
        try:
            if action == "navigate":
                url = instruction["url"]
                page.goto(url, wait_until="domcontentloaded")
                time.sleep(2)
                
                screenshot = page.screenshot()
                screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
                
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": "step",
                        "message": f"Step {step_num}: Navigated to {url}",
                        "action": f"Navigate to {url}"
                    }),
                    asyncio.get_event_loop()
                )
                
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": "screenshot",
                        "data": f"data:image/png;base64,{screenshot_b64}",
                        "description": f"Step {step_num}: Navigated to {url}"
                    }),
                    asyncio.get_event_loop()
                )
                
            elif action == "search":
                query = instruction["query"]
                
                # Try multiple search strategies
                search_selectors = [
                    'input[name="q"]',  # Google search box
                    'input[type="search"]',
                    'input[placeholder*="Search" i]',
                    'input[placeholder*="search" i]',
                    'input[aria-label*="Search" i]',
                    'input[title*="Search" i]',
                    '#search',
                    '.search-input',
                    '[data-testid="search"]'
                ]
                
                searched = False
                for selector in search_selectors:
                    try:
                        search_box = page.wait_for_selector(selector, timeout=3000)
                        if search_box:
                            search_box.click()
                            time.sleep(0.5)
                            search_box.fill(query)
                            time.sleep(0.5)
                            
                            # Try to submit the search
                            search_box.press("Enter")
                            time.sleep(3)  # Wait for search results
                            searched = True
                            break
                    except Exception as e:
                        logger.debug(f"Search selector {selector} failed: {e}")
                        continue
                
                message = f"Step {step_num}: Searched for '{query}'" if searched else f"Step {step_num}: Could not find search box"
                msg_type = "step" if searched else "warning"
                
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": msg_type,
                        "message": message,
                        "action": f"Search for {query}"
                    }),
                    asyncio.get_event_loop()
                )
                
                screenshot = page.screenshot()
                screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
                
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": "screenshot",
                        "data": f"data:image/png;base64,{screenshot_b64}",
                        "description": f"Step {step_num}: Search for {query}"
                    }),
                    asyncio.get_event_loop()
                )
                
            elif action == "fill":
                field = instruction["field"]
                value = instruction["value"]
                
                # Try multiple selector strategies
                selectors = [
                    f'input[name="{field}"]',
                    f'input[id="{field}"]', 
                    f'input[placeholder*="{field}" i]',
                    f'input[aria-label*="{field}" i]',
                    f'[name="{field}"]',
                    f'#{field}',
                    f'textarea[name="{field}"]',
                    f'textarea[placeholder*="{field}" i]'
                ]
                
                filled = False
                for selector in selectors:
                    try:
                        element = page.wait_for_selector(selector, timeout=2000)
                        if element:
                            element.click()
                            time.sleep(0.3)
                            element.fill(value)
                            filled = True
                            break
                    except:
                        continue
                
                message = f"Step {step_num}: Filled '{field}' with '{value}'" if filled else f"Step {step_num}: Could not find field '{field}'"
                msg_type = "step" if filled else "warning"
                
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": msg_type,
                        "message": message,
                        "action": f"Fill {field}"
                    }),
                    asyncio.get_event_loop()
                )
                
                screenshot = page.screenshot()
                screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
                
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": "screenshot",
                        "data": f"data:image/png;base64,{screenshot_b64}",
                        "description": f"Step {step_num}: Fill {field}"
                    }),
                    asyncio.get_event_loop()
                )
                
            elif action == "click":
                element_text = instruction["element"]
                
                # Enhanced click strategies
                click_strategies = [
                    # First result specific selectors
                    ('h3:first-of-type', 'first result heading'),
                    ('a[href]:has(h3):first-of-type', 'first result link with heading'),
                    ('.g:first-of-type a[href]', 'first Google result link'),
                    ('[data-testid="result"]:first-of-type a', 'first result by test id'),
                    
                    # Button and link selectors
                    (f'button:has-text("{element_text}")', 'button with text'),
                    (f'input[type="submit"][value*="{element_text}" i]', 'submit button'),
                    (f'input[type="button"][value*="{element_text}" i]', 'input button'),
                    (f'a:has-text("{element_text}")', 'link with text'),
                    (f'[role="button"]:has-text("{element_text}")', 'role button'),
                    
                    # Generic selectors
                    (f'*:text-is("{element_text}")', 'exact text match'),
                    (f'*:text("{element_text}")', 'partial text match')
                ]
                
                clicked = False
                for selector, description in click_strategies:
                    try:
                        element = page.wait_for_selector(selector, timeout=2000)
                        if element and element.is_visible():
                            element.click()
                            time.sleep(2)  # Wait after click
                            clicked = True
                            logger.info(f"Clicked using {description}: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"Click strategy '{description}' failed: {e}")
                        continue
                
                message = f"Step {step_num}: Clicked '{element_text}'" if clicked else f"Step {step_num}: Could not find element '{element_text}'"
                msg_type = "step" if clicked else "warning"
                
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": msg_type,
                        "message": message,
                        "action": f"Click {element_text}"
                    }),
                    asyncio.get_event_loop()
                )
                
                screenshot = page.screenshot()
                screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
                
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": "screenshot",
                        "data": f"data:image/png;base64,{screenshot_b64}",
                        "description": f"Step {step_num}: Click {element_text}"
                    }),
                    asyncio.get_event_loop()
                )
                
            elif action == "wait":
                duration = int(instruction["duration"])
                time.sleep(duration)
                
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({
                        "type": "step",
                        "message": f"Step {step_num}: Waited {duration} seconds",
                        "action": f"Wait {duration}s"
                    }),
                    asyncio.get_event_loop()
                )
                
        except Exception as e:
            logger.error(f"Error executing instruction {instruction}: {e}")
            asyncio.run_coroutine_threadsafe(
                self._broadcast({
                    "type": "error",
                    "message": f"Step {step_num} failed: {str(e)}",
                    "action": f"Error in {action}"
                }),
                asyncio.get_event_loop()
            )

    async def _run_simulation_mode(self, req: TaskRequest):
        """Fallback simulation mode when Playwright is not available"""
        await self._broadcast({
            "type": "step",
            "message": "Running in simulation mode (Playwright not available)",
            "action": "Simulation mode"
        })
        
        instructions = self._parse_instructions(req.task)
        
        for i, instruction in enumerate(instructions):
            if self.is_paused_flag:
                while self.is_paused_flag and self.state.status == "paused":
                    await asyncio.sleep(0.5)
            
            await asyncio.sleep(1)
            await self._broadcast({
                "type": "step",
                "message": f"Step {i+1}: Simulating {instruction['action']} - {instruction.get('query', instruction.get('field', instruction.get('element', instruction.get('url', 'action'))))}",
                "action": f"Simulate {instruction['action']}"
            })
        
        self.state.status = "completed"
        await self._broadcast({
            "type": "status",
            "status": "completed",
            "message": "Simulation completed"
        })

    def _parse_instructions(self, task: str) -> List[Dict[str, str]]:
        """Enhanced instruction parsing for complex tasks"""
        instructions = []
        task_lower = task.lower().strip()
        
        logger.info(f"Parsing task: {task}")
        
        # Handle search queries specifically
        search_patterns = [
            r'search\s+for\s+[\'"]([^"\']+)[\'"](?:\s+(?:and|then)\s+click\s+(?:on\s+)?(?:the\s+)?([^,\.]+))?',
            r'search\s+[\'"]([^"\']+)[\'"](?:\s+(?:and|then)\s+click\s+(?:on\s+)?(?:the\s+)?([^,\.]+))?',
            r'look\s+(?:up|for)\s+[\'"]([^"\']+)[\'"](?:\s+(?:and|then)\s+click\s+(?:on\s+)?(?:the\s+)?([^,\.]+))?'
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, task_lower)
            if match:
                query = match.group(1)
                instructions.append({"action": "search", "query": query})
                
                # If there's a click instruction after the search
                if match.group(2):
                    click_target = match.group(2).strip()
                    instructions.append({"action": "click", "element": click_target})
                
                logger.info(f"Parsed search instruction: search for '{query}'" + (f" then click '{click_target}'" if match.group(2) else ""))
                return instructions
        
        # If not a search, split by common delimiters and parse each part
        steps = re.split(r'[;,\n]|(?:\s+(?:then|and then|next|after that)\s+)', task, flags=re.IGNORECASE)
        
        for step in steps:
            step = step.strip()
            if not step:
                continue
                
            instruction = self._parse_single_instruction(step)
            if instruction:
                instructions.append(instruction)
        
        logger.info(f"Parsed {len(instructions)} instructions: {instructions}")
        return instructions

    def _parse_single_instruction(self, step: str) -> Optional[Dict[str, str]]:
        """Parse a single instruction step with enhanced patterns"""
        step = step.strip()
        step_lower = step.lower()
        
        # Search instruction
        search_match = re.search(r'search\s+(?:for\s+)?[\'"]([^"\']+)[\'"]', step_lower)
        if search_match:
            return {"action": "search", "query": search_match.group(1)}
        
        # Navigate to URL
        url_match = re.search(r'(?:go to|navigate to|visit|open)\s+([^\s,;]+)', step_lower)
        if url_match:
            return {"action": "navigate", "url": url_match.group(1)}
        
        # Fill input field - enhanced patterns
        fill_patterns = [
            r'(?:enter|type|input)\s+[\'"]([^"\']+)["\']\s+(?:into|in)\s+(?:the\s+)?[\'"]?([^"\']+)[\'"]?\s*(?:field|input|box)?',
            r'fill\s+[\'"]?([^"\']+)[\'"]?\s+(?:field\s+)?with\s+[\'"]([^"\']+)[\'"]',
            r'(?:fill|enter)\s+([^"\']+)\s+(?:field|input)?\s*(?:with|as)\s+[\'"]([^"\']+)[\'"]'
        ]
        
        for pattern in fill_patterns:
            fill_match = re.search(pattern, step_lower)
            if fill_match:
                if 'with' in step_lower:
                    return {"action": "fill", "field": fill_match.group(1), "value": fill_match.group(2)}
                else:
                    return {"action": "fill", "value": fill_match.group(1), "field": fill_match.group(2)}
        
        # Click button/element - enhanced patterns
        click_patterns = [
            r'click\s+(?:on\s+)?(?:the\s+)?[\'"]?([^"\']+)[\'"]?(?:\s+(?:button|link|result))?',
            r'(?:press|tap)\s+(?:the\s+)?[\'"]?([^"\']+)[\'"]?',
            r'select\s+(?:the\s+)?[\'"]?([^"\']+)[\'"]?'
        ]
        
        for pattern in click_patterns:
            click_match = re.search(pattern, step_lower)
            if click_match:
                return {"action": "click", "element": click_match.group(1)}
        
        # Wait instruction
        wait_match = re.search(r'wait\s+(\d+)\s*(?:seconds?|ms)?', step_lower)
        if wait_match:
            return {"action": "wait", "duration": wait_match.group(1)}
        
        # Submit/press enter
        if any(keyword in step_lower for keyword in ['submit', 'press enter', 'hit enter']):
            return {"action": "submit"}
        
        return None

    async def pause_agent(self):
        """Pause the agent"""
        self.is_paused_flag = True
        self.state.status = "paused"
        await self._broadcast({
            "type": "status",
            "status": "paused",
            "message": "Agent paused"
        })
        logger.info("Agent paused")

    async def resume_agent(self):
        """Resume the agent"""
        self.is_paused_flag = False
        self.state.status = "running"
        await self._broadcast({
            "type": "status",
            "status": "running",
            "message": "Agent resumed"
        })
        logger.info("Agent resumed")

    async def stop_agent(self):
        """Stop the agent"""
        self.state.status = "stopping"
        await self._broadcast({
            "type": "status",
            "status": "stopping",
            "message": "Stopping agent..."
        })
        
        await self._cleanup()
        
        self.state.status = "idle"
        self.is_paused_flag = False
        await self._broadcast({
            "type": "status",
            "status": "idle",
            "message": "Agent stopped"
        })
        logger.info("Agent stopped")

    async def _cleanup(self):
        """Clean up browser resources"""
        try:
            # Cleanup is handled by the context manager in sync mode
            pass
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "status": self.state.status,
            "steps_completed": self.state.steps_completed,
            "current_action": self.state.current_action,
            "start_time": self.state.start_time.isoformat() if self.state.start_time else None,
            "task_id": self.task_id,
            "is_paused": self.is_paused_flag
        }