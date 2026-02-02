"""Application settings management using Pydantic."""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#2797923

class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Google Gemini Configuration (optional - only if using Gemini)
    google_api_key: str = Field(default="", description="Google Gemini API key (optional)")
    llm_model_name: str = Field(default="gemini-pro-latest", description="LLM model name to use for all agents")

    # Groq Configuration
    groq_api_key: str = Field(..., description="Groq API key")
    llm_model_name_groq: str = Field(default="llama-3.1-8b-instant", description="Groq LLM model name to use for all agents")

    # Agent Configuration
    max_iterations: int = Field(default=3, ge=1, le=10)
    execution_timeout: int = Field(default=60, ge=10, le=300)
    agent_temperature: float = Field(default=0.1, ge=0.0, le=1.0)

    # PostgreSQL Configuration
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_user: str = Field(default="postgres")
    db_password: str = Field(default="devpass")
    db_name: str = Field(default="customer_db")

    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_file: str = Field(default="logs/app.log")

    # Code Execution Safety
    enable_code_execution: bool = Field(default=True)
    max_memory_mb: int = Field(default=512, ge=128, le=2048)
    allow_network_access: bool = Field(default=True)

    # Session Management
    enable_session_persistence: bool = Field(default=True)
    session_storage_path: str = Field(default="outputs/sessions")

    # UI Configuration
    streamlit_server_port: int = Field(default=8501)
    streamlit_server_address: str = Field(default="localhost")

    @field_validator("groq_api_key")
    @classmethod
    def validate_groq_api_key(cls, v: str) -> str:
        """Validate Groq API key is not empty or placeholder."""
        if not v or v == "your_groq_api_key_here":
            raise ValueError(
                "GROQ_API_KEY must be set in .env file. "
                "Get your key from https://console.groq.com/keys"
            )
        return v

    @property
    def db_connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def get_project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        root = self.get_project_root()

        directories = [
            root / "logs",
            root / "outputs",
            root / self.session_storage_path,
            root / "outputs" / "generated_code",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
settings.ensure_directories()
