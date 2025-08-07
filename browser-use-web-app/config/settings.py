import os
from pathlib import Path
from typing import List, Union
from pydantic_settings import BaseSettings

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Server configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # Browser settings
    BROWSER_HEADLESS: bool = False
    BROWSER_TIMEOUT: int = 30000
    SCREENSHOT_TIMEOUT: int = 5000
    
    # Security - Handle ALLOWED_ORIGINS specially
    SECRET_KEY: str = "browser-use-secret-key-change-in-production"
    ALLOWED_ORIGINS: Union[List[str], str] = "*"
    
    # Default LLM settings (optional - can be overridden in UI)
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_MODEL: str = "gpt-4"
    
    # API Keys (optional - can be entered in UI)
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # File upload settings
    MAX_FILE_SIZE: int = 10_000_000  # 10MB
    UPLOAD_DIR: Path = PROJECT_ROOT / "uploads"
    
    # Logging
    LOG_FILE: Path = PROJECT_ROOT / "agent.log"
    
    # Agent settings
    MAX_STEPS: int = 50
    STEP_TIMEOUT: int = 10
    MAX_RETRIES: int = 3
    
    # WebSocket settings
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_RECONNECT_ATTEMPTS: int = 5
    
    def model_post_init(self, __context) -> None:
        """Post-initialization processing"""
        # Handle ALLOWED_ORIGINS - convert string to list if needed
        if isinstance(self.ALLOWED_ORIGINS, str):
            if self.ALLOWED_ORIGINS == "*":
                self.ALLOWED_ORIGINS = ["*"]
            else:
                # Split comma-separated values
                self.ALLOWED_ORIGINS = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        
        # Create upload directory if it doesn't exist
        self.UPLOAD_DIR.mkdir(exist_ok=True)
    
    class Config:
        env_file = PROJECT_ROOT / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Don't try to parse simple strings as JSON
        env_parse_none_str = 'None'

# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get application settings (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
        
    return _settings

# Environment-specific configurations
def get_dev_settings() -> Settings:
    """Development environment settings"""
    settings = get_settings()
    settings.LOG_LEVEL = "DEBUG"
    settings.HOST = "127.0.0.1"
    return settings

def get_prod_settings() -> Settings:
    """Production environment settings"""
    settings = get_settings()
    settings.LOG_LEVEL = "WARNING"
    settings.ALLOWED_ORIGINS = ["https://yourdomain.com"]
    return settings

# Utility functions for settings
def is_development() -> bool:
    """Check if running in development mode"""
    return os.getenv("ENVIRONMENT", "development").lower() == "development"

def get_api_key(provider: str) -> str:
    """Get API key for a specific provider from environment"""
    settings = get_settings()
    
    if provider == "openai":
        return settings.OPENAI_API_KEY
    elif provider == "gemini":
        return settings.GOOGLE_API_KEY
    elif provider == "anthropic":
        return settings.ANTHROPIC_API_KEY
    
    return ""

def validate_environment():
    """Validate that all required environment variables are set"""
    settings = get_settings()
    errors = []
    
    # Check for required directories
    if not settings.UPLOAD_DIR.exists():
        try:
            settings.UPLOAD_DIR.mkdir(exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create upload directory: {e}")
    
    # Validate port range
    if not (1024 <= settings.PORT <= 65535):
        errors.append(f"Invalid port number: {settings.PORT}")
    
    # Validate log level
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if settings.LOG_LEVEL.upper() not in valid_log_levels:
        errors.append(f"Invalid log level: {settings.LOG_LEVEL}")
    
    if errors:
        raise ValueError("Environment validation failed:\n" + "\n".join(errors))
    
    return True