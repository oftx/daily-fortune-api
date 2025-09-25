from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from .core.config import settings

# --- THIS IS THE FIX ---
# Add tz_aware=True to the client constructor.
# This ensures all dates read from MongoDB are timezone-aware (UTC).
client = AsyncIOMotorClient(settings.DATABASE_URL, tz_aware=True)
# --- END OF FIX ---

db: AsyncIOMotorDatabase = client[settings.DATABASE_NAME]

async def get_db() -> AsyncIOMotorDatabase:
    return db