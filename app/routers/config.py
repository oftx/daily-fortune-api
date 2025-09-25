# app/routers/config.py

from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db import get_db
from ..core.rate_limiter import limiter_decorator

router = APIRouter(prefix="/config", tags=["Config"])

@router.get("/registration-status")
@limiter_decorator("60/minute") # Protect this public endpoint
async def get_registration_status(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    config = await db.config.find_one({"key": "registration_status"})
    is_open = config.get("value", False) if config else False
    return {"is_open": is_open}