"""
Browser-Use Web Agent Backend

A FastAPI-based backend for browser automation using natural language instructions.
"""

__version__ = "1.0.0"
__author__ = "Browser-Use Team"
__description__ = "Web-based browser automation with natural language instructions"

# Import main components for easy access
from .agent_manager import AgentManager
from .models import TaskRequest, AgentState
from .utils import get_llm_instance, validate_api_key

__all__ = [
    "AgentManager",
    "TaskRequest", 
    "AgentState",
    "get_llm_instance",
    "validate_api_key"
]