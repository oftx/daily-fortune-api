from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from typing import List

from ..db import get_db
from ..services.fortune_service import draw_fortune_logic, FORTUNE_RANKS
from ..models.user import UserInDB
from ..models.fortune import LeaderboardGroup, LeaderboardUser
from ..models.db_models import User, Fortune
from .dependencies import get_optional_current_user
from ..core.rate_limiter import limiter_decorator
from ..core.time_service import get_current_day_start_in_utc, get_next_day_start_in_utc

router = APIRouter(prefix="/fortune", tags=["Fortune"])


@router.post("/draw")
@limiter_decorator("30/minute")
async def draw(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB | None = Depends(get_optional_current_user),
):
    if not current_user:
        return {"fortune": draw_fortune_logic()}

    if current_user.status != "active":
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    user_pk = int(current_user.id)
    today_start = get_current_day_start_in_utc()
    tomorrow_start = today_start + timedelta(days=1)

    user = (await db.execute(select(User).where(User.id == user_pk))).scalar_one_or_none()
    if user:
        user.last_active_date = datetime.now(timezone.utc)

    existing = (await db.execute(
        select(Fortune).where(
            Fortune.user_id == user_pk,
            Fortune.created_at >= today_start,
            Fortune.created_at < tomorrow_start,
        )
    )).scalar_one_or_none()

    if existing:
        await db.commit()
        return {"fortune": existing.value, "next_draw_at": get_next_day_start_in_utc()}

    value = draw_fortune_logic()
    db.add(Fortune(
        user_id=user_pk,
        date=today_start.date(),
        value=value,
        created_at=datetime.now(timezone.utc),
    ))
    await db.commit()
    return {"fortune": value, "next_draw_at": get_next_day_start_in_utc()}


@router.get("/leaderboard", response_model=List[LeaderboardGroup])
@limiter_decorator("60/minute")
async def get_todays_leaderboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    today_start = get_current_day_start_in_utc()
    tomorrow_start = today_start + timedelta(days=1)

    rows = (await db.execute(
        select(Fortune.value, User.username, User.display_name)
        .join(User, User.id == Fortune.user_id)
        .where(
            Fortune.created_at >= today_start,
            Fortune.created_at < tomorrow_start,
        )
    )).all()

    grouped: dict = {}
    for value, username, display_name in rows:
        grouped.setdefault(value, []).append(
            LeaderboardUser(username=username, display_name=display_name)
        )

    result = [
        LeaderboardGroup(fortune=k, users=v)
        for k, v in grouped.items()
    ]
    result.sort(key=lambda g: FORTUNE_RANKS.get(g.fortune, 0), reverse=True)
    return result
