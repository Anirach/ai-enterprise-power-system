"""
AI Power System - Configuration
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application
    app_secret_key: str = "your-secret-key-change-in-production"
    app_debug: bool = False
    app_log_level: str = "INFO"
    
    # Database
    database_url: str = "postgresql://aipower:password@localhost:5432/aipower_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.2:3b"
    ollama_embedding_model: str = "nomic-embed-text"
    
    # Upload settings
    upload_dir: str = "/app/uploads"
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


