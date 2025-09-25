# app/core/config.py

from pydantic_settings import BaseSettings
from typing import List, Union

class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_NAME: str
    
    RATE_LIMITING_ENABLED: bool = False 
    REDIS_URL: str = "redis://localhost:6379"
    
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    APP_TIMEZONE: str = "UTC" 
    DAY_RESET_OFFSET_SECONDS: int = 0
    
    # --- NEW: Centralized Domain and CORS Configuration ---
    # The domain for the API server itself. Example: api.yourdomain.com
    API_DOMAIN: str = "localhost"
    
    # A comma-separated string of allowed frontend origins for CORS.
    # Example: "https://app.yourdomain.com,https://admin.yourdomain.com"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Helper property to convert the comma-separated string to a list
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"

settings = Settings()