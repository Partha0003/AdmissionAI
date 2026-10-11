from pathlib import Path
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "AdmissionAI"
    ENVIRONMENT: str = "PROTOTYPE"

    # Institution Configuration (Default: XYZ Engineering College)
    INSTITUTION_NAME: str = "XYZ Engineering College"
    INSTITUTION_CODE: str = "XYZ"
    ACADEMIC_YEAR: str = "2026-27"

    # Security
    SECRET_KEY: str = "admissionai-super-secret-prototype-key-2026-27"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{(BACKEND_DIR / 'admissionai.db').as_posix()}"
    SYNC_DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'admissionai.db').as_posix()}"

    @field_validator("DATABASE_URL", mode="before")
    def assemble_async_db_url(cls, v: str) -> str:
        if v and v.startswith("sqlite+aiosqlite:///."):
            rel_path = v.replace("sqlite+aiosqlite:///.", "").lstrip("/\\")
            abs_path = (BACKEND_DIR / rel_path).as_posix()
            return f"sqlite+aiosqlite:///{abs_path}"
        return v

    @field_validator("SYNC_DATABASE_URL", mode="before")
    def assemble_sync_db_url(cls, v: str) -> str:
        if v and v.startswith("sqlite:///."):
            rel_path = v.replace("sqlite:///.", "").lstrip("/\\")
            abs_path = (BACKEND_DIR / rel_path).as_posix()
            return f"sqlite:///{abs_path}"
        return v

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Mock Integrations
    MOCK_TNEA_ENABLED: bool = True
    MOCK_ERP_ENABLED: bool = True
    MOCK_PAYMENT_ENABLED: bool = True
    MOCK_NOTIFICATION_ENABLED: bool = True

    # OCR Configuration
    OCR_ENGINE: str = "tesseract"  # Options: 'tesseract', 'mock'
    OCR_LANGUAGE: str = "eng"
    TESSERACT_CMD: Union[str, None] = None


settings = Settings()
