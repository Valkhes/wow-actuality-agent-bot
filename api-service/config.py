import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google/Gemini Configuration
    google_api_key: str
    
    # ChromaDB Configuration
    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000
    chromadb_collection: str = "wow_articles"
    
    # Langfuse Configuration
    langfuse_secret_key: Optional[str] = None
    langfuse_public_key: Optional[str] = None
    langfuse_host: str = "http://langfuse:3000"
    
    # LiteLLM Gateway Configuration
    litellm_gateway_url: Optional[str] = None
    
    # AI Model Configuration
    ai_model_name: str = "gemini-2.0-flash-exp"
    ai_temperature: float = 0.7
    ai_max_tokens: int = 1000
    max_context_documents: int = 5
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # API Configuration
    api_port: int = 8000
    api_host: str = "0.0.0.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()