from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import timedelta
from pydantic import BaseModel

from ..db import get_db
from ..models.user import UserInDB, UserMeProfile
from ..models.db_models import User, Fortune
from .dependencies import get_current_user, _user_to_schema
from ..core.time_service import get_current_day_start_in_utc

router = APIRouter(prefix="/admin", tags=["Administration"])


class StatusUpdate(BaseModel):
    status: str


class VisibilityUpdate(BaseModel):
    is_hidden: bool


class TagsUpdate(BaseModel):
    tags: List[str]


async def get_current_admin_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


@router.get("/users", response_model=List[UserMeProfile])
async def read_all_users(
    admin_user: UserInDB = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    users = (await db.execute(select(User))).scalars().all()

    today_start = get_current_day_start_in_utc()
    tomorrow_start = today_start + timedelta(days=1)

    result = []
    for u in users:
        total_draws = (await db.execute(
            select(func.count()).select_from(Fortune).where(Fortune.user_id == u.id)
        )).scalar_one()

        todays = (await db.execute(
            select(Fortune).where(
                Fortune.user_id == u.id,
                Fortune.created_at >= today_start,
                Fortune.created_at < tomorrow_start,
            )
        )).scalar_one_or_none()

        schema = _user_to_schema(u)
        result.append(UserMeProfile(
            **schema.model_dump(),
            total_draws=total_draws,
            has_drawn_today=todays is not None,
            todays_fortune=todays.value if todays else None,
        ))
    return result


@router.post("/users/{user_id}/status", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_status(
    user_id: str,
    status_update: StatusUpdate,
    admin_user: UserInDB = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    if status_update.status not in ["active", "inactive"]:
        raise HTTPException(status_code=400, detail="Invalid status value")

    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.status = status_update.status
    await db.commit()
    return


@router.post("/users/{user_id}/visibility", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_visibility(
    user_id: str,
    visibility_update: VisibilityUpdate,
    admin_user: UserInDB = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_hidden = visibility_update.is_hidden
    await db.commit()
    return


@router.post("/users/{user_id}/tags", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_tags(
    user_id: str,
    tags_update: TagsUpdate,
    admin_user: UserInDB = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.tags = tags_update.tags
    await db.commit()
    return
