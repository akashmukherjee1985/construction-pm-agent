# app/config.py

from pydantic_settings import BaseSettings
from pathlib import Path

from typing import ClassVar

# Build an absolute path to the project root directory
# __file__ is the path to this config.py file
# .parent gives the folder containing it (app/)
# .parent again gives the folder containing app/ (project root)
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """
    All configuration for the application lives here.
    
    Pydantic reads these values from environment variables or a .env file.
    The variable names here must match the names in your .env file exactly,
    but they are case-insensitive (DATABASE_URL = database_url = fine).
    
    If a variable has a default value, it's optional in .env.
    If it has no default, it MUST be set in .env or the app crashes on startup.
    This is intentional — you want to know immediately if config is missing.
    """

    # ── LLM Configuration ──────────────────────────────────────────
    # Which Ollama model to use for the agent
    LLM_MODEL: str = "llama3.1:8b"

    # Ollama server address — matches our OLLAMA_HOST environment variable
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Temperature for SQL generation — low for precision
    LLM_TEMPERATURE_SQL: float = 0.0

    # Temperature for conversational responses — higher for natural language
    LLM_TEMPERATURE_CHAT: float = 0.7

    # ── Database Configuration ──────────────────────────────────────
    # Path to the SQLite database file
    # We use an absolute path built from PROJECT_ROOT so it works
    # regardless of where you run the script from
    # BASE_DIR = Path(__file__).resolve().parent.parent
    # BASE_DIR: Path = Path(__file__).resolve().parent.parent
    BASE_DIR: ClassVar[Path] = Path(__file__).resolve().parent.parent
    # DATABASE_URL = f"sqlite:///{BASE_DIR}/data/construction.db"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/construction.db"

    # ── API Configuration ───────────────────────────────────────────
    # FastAPI server settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # ── Application Configuration ───────────────────────────────────
    # Name shown in API docs and UI
    APP_NAME: str = "Construction PM Agent"
    APP_VERSION: str = "0.1.0"

    # How many conversation turns to keep in memory
    # Beyond this number, oldest turns are dropped
    MAX_CONVERSATION_HISTORY: int = 20

    # ── Logging Configuration ───────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = str(PROJECT_ROOT / "logs" / "app.log")

    class Config:
        """
        Tell Pydantic where to find the .env file.
        env_file = ".env" means look for .env in the current working directory.
        extra = "ignore" means if .env has extra variables we don't define
        here, don't crash — just ignore them.
        """
        env_file = ".env"
        extra = "ignore"


# Create a single instance of Settings
# This is the object the rest of the app imports
# It's created once when the module is first imported
# and reused everywhere — this pattern is called a Singleton
settings = Settings()