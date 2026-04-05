# Config (API keys, env)
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Settings:
    # Build knowledge base
    FOLDER_DATA_BUILD_KB: str = os.getenv('FOLDER_DATA_BUILD_KB', 'data')
    
    # Knowledge base embedding
    GOOGLE_API_KEY: str | None = os.getenv('GOOGLE_API_KEY')
    KB_EMBEDDING_BATCH_SIZE: int = int(os.getenv('KB_EMBEDDING_BATCH_SIZE', '100'))
    KB_EMBEDDING_REQUEST_DELAY_SECONDS: float = float(os.getenv('KB_EMBEDDING_REQUEST_DELAY_SECONDS', '60'))
    KB_EMBEDDING_MAX_RETRIES: int = int(os.getenv('KB_EMBEDDING_MAX_RETRIES', '5'))

    # PostgreSQL / pgvector
    POSTGRES_URL: str = os.getenv('POSTGRES_URL', '')
    KB_VECTOR_TABLE: str = os.getenv('KB_VECTOR_TABLE', 'kb_embeddings')
    KB_EMBEDDING_DIMENSION: int = int(os.getenv('KB_EMBEDDING_DIMENSION', '3072'))
    KB_RETRIEVER_BACKEND: str = os.getenv('KB_RETRIEVER_BACKEND', 'postgres')

    # Search service integration
    SEARCH_SERVICE_URL: str = os.getenv('SEARCH_SERVICE_URL', 'http://localhost:8001/search')
    SEARCH_SERVICE_TIMEOUT_SECONDS: float = float(os.getenv('SEARCH_SERVICE_TIMEOUT_SECONDS', '5'))
    SEARCH_SERVICE_MAX_PAGE_SIZE: int = int(os.getenv('SEARCH_SERVICE_MAX_PAGE_SIZE', '50'))



settings = Settings()