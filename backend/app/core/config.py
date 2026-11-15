from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # the backend/ folder


class Settings(BaseSettings):
    PROJECT_NAME: str = "SwasthyaVaani"

    DATABASE_URL: str
    SECRET_KEY: str

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Prescription uploads
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_UPLOAD_MB: int = 10

    # AI provider: "mock" (no key needed, sample output), "gemini", "anthropic" or "openai"
    AI_PROVIDER: str = "mock"
    AI_API_KEY: str = ""
    AI_MODEL: str = ""          # leave empty to use the provider's default below
    AI_TIMEOUT_SECONDS: int = 90

    # Origins allowed to call the API from a browser (comma separated)
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
