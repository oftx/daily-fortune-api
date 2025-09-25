# app/core/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_NAME: str
    
    RATE_LIMITING_ENABLED: bool = False 
    REDIS_URL: str = "redis://localhost:6379"
    
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # --- NEW: Timezone and Day Reset Configuration ---
    # The IANA timezone name for the application's business logic.
    # Example: "Asia/Shanghai", "America/New_York", "UTC"
    APP_TIMEZONE: str = "UTC" 
    
    # An offset in seconds to adjust the start of a new day.
    # 0 means the day resets at 00:00 in APP_TIMEZONE.
    # 3600 means the day resets at 01:00 in APP_TIMEZONE.
    # -3600 means the day resets at 23:00 of the previous day in APP_TIMEZONE.
    DAY_RESET_OFFSET_SECONDS: int = 0

    class Config:
        env_file = ".env"

settings = Settings()