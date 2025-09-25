# app/core/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_NAME: str
    
    # --- NEW: Rate Limiting Configuration ---
    # This acts as a feature flag. Defaults to False.
    RATE_LIMITING_ENABLED: bool = False 
    # Default Redis URL, can be overridden by .env
    REDIS_URL: str = "redis://localhost:6379"
    
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    class Config:
        env_file = ".env"

settings = Settings()