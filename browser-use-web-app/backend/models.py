from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any

class TaskRequest(BaseModel):
    task: str
    api_key: str
    llm_provider: str = "openai"
    model: str = "gpt-4"
    context: Dict[str, Any] = {}
    max_steps: int = 50
    headless: bool = False

class AgentState(BaseModel):
    status: str = "idle"
    steps_completed: int = 0
    current_action: str = ""
    start_time: datetime = None
