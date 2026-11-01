import os
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")

class Settings(BaseSettings):
    PROJECT_NAME: str = "DataPilot API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "datapilot_super_secret_jwt_key_change_in_production_32chars")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # AES-256 requires 32 bytes key for Fernet or AES-GCM
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "datapilot_aes256_secret_key_32bytes_long!!")
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'datapilot.db')}")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    DUCKDB_DIR: str = os.getenv("DUCKDB_DIR", os.path.join(DATA_DIR, "duckdb"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(DATA_DIR, "uploads"))
    SANDBOX_DIR: str = os.getenv("SANDBOX_DIR", os.path.join(DATA_DIR, "sandboxes"))
    
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "gemini")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()

def get_duckdb_path(source_id: str) -> str:
    os.makedirs(settings.DUCKDB_DIR, exist_ok=True)
    return os.path.join(settings.DUCKDB_DIR, f"{source_id}.duckdb")

