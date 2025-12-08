from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration settings."""
    SECRET_KEY: str = "YOUR_SUPER_SECRET_JWT_KEY_CHANGE_ME"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "sqlite+aiosqlite:///./sql_app.db"

    class Config:
        env_file = ".env"

settings = Settings()