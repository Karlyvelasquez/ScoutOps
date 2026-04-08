import os
from pathlib import Path
from pydantic_settings import BaseSettings

root_dir = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    gemini_api_key: str
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.3
    max_output_tokens: int = 2048
    log_level: str = "INFO"
    incidents_data_dir: str = "./data/incidents"
    backend_port: int = 8000
    
    class Config:
        env_file = str(root_dir / ".env")
        case_sensitive = False

settings = Settings()
