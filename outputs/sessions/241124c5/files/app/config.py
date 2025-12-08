from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Database settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./todo.db"
    
    # JWT settings
    SECRET_KEY: str = "a-very-secret-key-that-should-be-changed"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()