from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Database settings (Defaulting to PostgreSQL setup for Docker)
    DATABASE_URL: str = "postgresql+psycopg2://user:password@db:5432/todo_db"
    
    # JWT settings
    SECRET_KEY: str = "super-secret-key-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Configuration setup
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()