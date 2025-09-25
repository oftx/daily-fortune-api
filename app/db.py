from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from .core.config import settings

client = AsyncIOMotorClient(settings.DATABASE_URL)
db: AsyncIOMotorDatabase = client[settings.DATABASE_NAME]

async def get_db() -> AsyncIOMotorDatabase:
    return db
