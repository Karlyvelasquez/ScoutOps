from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    llm_provider: str = "gemini"
    gemini_api_key: str
    openai_api_key: Optional[str] = None
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.3
    max_output_tokens: int = 2048
    log_level: str = "INFO"
    incidents_data_dir: str = "./data/incidents"
    backend_port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
