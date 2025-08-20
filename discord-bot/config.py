import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Discord Configuration
    discord_bot_token: str
    discord_guild_id: Optional[str] = None
    
    # API Service Configuration
    api_service_url: str = "http://api-service:8000"
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = 1
    max_question_length: int = 60
    max_response_length: int = 2000
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # Health check server
    health_check_port: int = 8001
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()