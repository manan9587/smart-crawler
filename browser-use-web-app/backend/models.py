from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional

class TaskRequest(BaseModel):
    """Request model for starting an agent task"""
    task: str = Field(..., description="The task instruction for the agent")
    api_key: str = Field(..., description="API key for the LLM provider")
    llm_provider: str = Field(default="openai", description="LLM provider (openai, gemini, etc.)")
    model: str = Field(default="gpt-4", description="Model name to use")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context like URL")
    max_steps: int = Field(default=50, description="Maximum number of steps to execute")
    headless: bool = Field(default=False, description="Whether to run browser in headless mode")
    timeout: int = Field(default=60, description="Timeout for the task in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task": "Go to https://example.com, fill username with 'testuser', fill password with 'secret', then click login",
                "api_key": "your-api-key-here",
                "llm_provider": "openai",
                "model": "gpt-4",
                "context": {"url": "https://example.com"},
                "max_steps": 50,
                "headless": False,
                "timeout": 60
            }
        }

class AgentState(BaseModel):
    """Current state of the agent"""
    status: str = Field(default="idle", description="Current status: idle, running, paused, completed, error")
    steps_completed: int = Field(default=0, description="Number of steps completed")
    current_action: str = Field(default="", description="Current action being performed")
    start_time: Optional[datetime] = Field(default=None, description="When the task started")
    error_message: Optional[str] = Field(default=None, description="Error message if any")
    
    class Config:
        arbitrary_types_allowed = True

class AgentResponse(BaseModel):
    """Response from agent operations"""
    status: str
    message: str
    task_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Optional[Dict[str, Any]] = None

class WebSocketMessage(BaseModel):
    """WebSocket message structure"""
    type: str = Field(..., description="Message type: step, status, screenshot, error, etc.")
    message: Optional[str] = Field(default=None, description="Human readable message")
    data: Optional[Any] = Field(default=None, description="Additional data payload")
    timestamp: datetime = Field(default_factory=datetime.now)
    action: Optional[str] = Field(default=None, description="Current action being performed")

class StepUpdate(BaseModel):
    """Update for a single step"""
    step_number: int
    action: str
    status: str  # pending, running, completed, failed
    message: str
    screenshot: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)