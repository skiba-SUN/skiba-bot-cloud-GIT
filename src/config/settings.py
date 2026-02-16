"""Settings and configuration management"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Configuration
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    model_name: str = Field(default="claude-sonnet-4-5-20250929", env="MODEL_NAME")
    max_tokens: int = Field(default=4096, env="MAX_TOKENS")
    temperature: float = Field(default=0.7, env="TEMPERATURE")

    # RAG Configuration
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    max_context_length: int = Field(default=200000, env="MAX_CONTEXT_LENGTH")

    # Cost Optimization
    enable_caching: bool = Field(default=True, env="ENABLE_CACHING")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default="logs/agent.log", env="LOG_FILE")

    # WhatsApp (Green API)
    green_api_instance_id: Optional[str] = Field(default=None, env="GREEN_API_INSTANCE_ID")
    green_api_token: Optional[str] = Field(default=None, env="GREEN_API_TOKEN")

    # Muay Thai Bot
    leads_excel_path: str = Field(default="data/leads.xlsx", env="LEADS_EXCEL_PATH")

    # Google Sheets
    google_sheet_id: Optional[str] = Field(default=None, env="GOOGLE_SHEET_ID")

    # Owner/Admin Settings
    eden_phone: Optional[str] = Field(default=None, env="EDEN_PHONE")

    # Project paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings():
    """Reset settings singleton (useful for testing)"""
    global _settings
    _settings = None
