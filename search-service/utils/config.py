"""Application settings."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    POSTGRES_URL: str = Field(default="")
    GOOGLE_API_KEY: str = Field(default="")
    SEARCH_SQL_MODEL: str = Field(default="models/gemini-3.1-flash-lite-preview")
    SEARCH_SQL_GENERATION_ENABLED: bool = Field(default=True)
    SEARCH_PRODUCTS_TABLE: str = Field(default="search_products")
    API_TITLE: str = Field(default="E-com Search Service")
    API_VERSION: str = Field(default="0.1.0")
    API_DESCRIPTION: str = Field(
        default="Dedicated product search API for LLM and downstream services."
    )
    MAX_PAGE_SIZE: int = Field(default=100)


settings = Settings()
