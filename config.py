from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # OpenRouter
    openrouter_api_key: str = "your_openrouter_api_key_here"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    # App
    app_name: str = "AI Learning Agent"
    app_url: str = "http://localhost:8501"
    secret_key: str = "changeme-in-production"

    # Database
    database_url: str = "sqlite+aiosqlite:///./learning_agent.db"

    # ChromaDB
    chroma_persist_dir: str = "./rag/vectorstore/chroma_db"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    debug: bool = True

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
