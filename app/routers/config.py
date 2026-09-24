from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.db_models import AppConfig
from ..core.rate_limiter import limiter_decorator

router = APIRouter(prefix="/config", tags=["Config"])


@router.get("/registration-status")
@limiter_decorator("60/minute")
async def get_registration_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    cfg = (await db.execute(
        select(AppConfig).where(AppConfig.key == "registration_status")
    )).scalar_one_or_none()
    is_open = bool(cfg.value) if cfg else False
    return {"is_open": is_open}
