"""Frontend configuration for the Recipe RAG Knowledge Graph Streamlit app."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (one level up from frontend/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


@dataclass
class FrontendConfig:
    """Configuration for the Streamlit frontend."""

    app_title: str = "Recipe Knowledge Graph"
    app_subtitle: str = "AI-powered recipe search with vector and graph intelligence"
    request_timeout: float = 120.0
    api_base_url: str = field(default_factory=lambda: "")

    def __post_init__(self) -> None:
        if not self.api_base_url:
            override = os.getenv("API_BASE_URL")
            if override:
                self.api_base_url = override.rstrip("/")
            else:
                port = os.getenv("APP_PORT", "8058")
                self.api_base_url = f"http://localhost:{port}"


config = FrontendConfig()
