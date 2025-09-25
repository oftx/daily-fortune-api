from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db import get_db

router = APIRouter(prefix="/config", tags=["Config"])

@router.get("/registration-status")
async def get_registration_status(db: AsyncIOMotorDatabase = Depends(get_db)):
    config = await db.config.find_one({"key": "registration_status"})
    is_open = config.get("value", False) if config else False
    return {"is_open": is_open}
