import os
from pydantic_settings import BaseSettings
from functools import lru_cache

# Root of the whole project (one level above backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings(BaseSettings):
    # OpenRouter
    openrouter_api_key: str = "your_openrouter_api_key_here"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    # App
    app_name: str = "AI Learning Agent"
    app_url: str = "http://localhost:8501"
    secret_key: str = "changeme-in-production"

    # Database — stored in project root
    database_url: str = f"sqlite+aiosqlite:///{PROJECT_ROOT}/learning_agent.db"

    # ChromaDB — stored in project root/rag/vectorstore
    chroma_persist_dir: str = os.path.join(PROJECT_ROOT, "rag", "vectorstore", "chroma_db")

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    debug: bool = True

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    class Config:
        # Look for .env in project root
        env_file = os.path.join(PROJECT_ROOT, ".env")
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()