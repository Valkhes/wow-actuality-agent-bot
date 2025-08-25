import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Blizzspirit Configuration
    blizzspirit_base_url: str = "https://www.blizzspirit.com"
    crawler_interval_hours: int = 24
    crawler_max_articles: int = 20
    
    # ChromaDB Configuration
    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000
    chromadb_collection: str = "wow_articles"
    
    # Crawler Configuration
    requests_per_second: float = 1.0
    concurrent_requests: int = 3
    request_timeout: int = 30
    
    # Cache Configuration
    cache_file: str = "cache/processed_urls.json"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # API Configuration - Railway uses dynamic PORT
    api_port: int = int(os.environ.get("PORT", 8002))
    api_host: str = "0.0.0.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()