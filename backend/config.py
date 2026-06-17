"""Configuration management for RAG Admin system."""

import os
import yaml
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "RAG Admin"
    app_version: str = "1.0.0"
    debug: bool = True

    # Paths
    base_dir: str = str(Path(__file__).parent.parent)
    upload_dir: str = ""
    data_dir: str = ""
    chroma_persist_dir: str = ""

    # Database
    database_url: str = "sqlite:///./data/rag_admin.db"

    # Embedding
    embedding_provider: str = "local"  # "local" or "openai"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"  # local model name
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None
    openai_embedding_model: str = "text-embedding-3-small"

    # LLM for QA
    llm_provider: str = "openai"  # "openai" or "local"
    llm_model: str = "deepseek-chat"
    llm_api_key: Optional[str] = None
    llm_api_base: Optional[str] = None

    # Chunking defaults
    default_chunk_size: int = 512
    default_chunk_overlap: int = 64
    default_top_k: int = 5

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Resolve paths after init
        self.upload_dir = self.upload_dir or os.path.join(self.base_dir, "uploads")
        self.data_dir = self.data_dir or os.path.join(self.base_dir, "data")
        self.chroma_persist_dir = os.path.join(self.data_dir, "chroma")

        # Ensure directories exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.chroma_persist_dir, exist_ok=True)


def load_config_from_yaml(path: Optional[str] = None) -> dict:
    """Load configuration from YAML file."""
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

    path = os.path.abspath(path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def get_settings() -> Settings:
    """Get application settings, merged with YAML config."""
    settings = Settings()

    yaml_config = load_config_from_yaml()

    # Merge YAML config into settings
    for key, value in yaml_config.items():
        key_upper = key.upper()
        if hasattr(settings, key_upper):
            setattr(settings, key_upper, value)

    return settings


settings = get_settings()
