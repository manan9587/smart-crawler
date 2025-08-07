from pydantic import BaseSettings
class Settings(BaseSettings):
    openai_api_key: str
    google_api_key: str
    anthropic_api_key: str
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = True
    class Config:
        env_file = ".env"
settings = Settings()
