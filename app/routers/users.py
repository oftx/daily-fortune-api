from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta

from ..db import get_db
from ..models.user import (
    UserInDB, UserMeProfile, UserPublicProfile, UserUpdate, PasswordUpdate,
)
from ..models.fortune import FortuneHistoryItem
from ..models.db_models import User, Fortune
from .dependencies import (
    get_current_user, get_current_active_user, get_optional_current_user,
    _user_to_schema,
)
from ..core.rate_limiter import limiter_decorator
from ..core.time_service import get_current_day_start_in_utc, get_next_day_start_in_utc
from ..core.security import verify_password, get_password_hash, create_access_token

router = APIRouter(prefix="/users", tags=["Users"])


async def _build_me_profile(db: AsyncSession, user: User) -> UserMeProfile:
    total_draws = (await db.execute(
        select(func.count()).select_from(Fortune).where(Fortune.user_id == user.id)
    )).scalar_one()

    today_start = get_current_day_start_in_utc()
    tomorrow_start = today_start + timedelta(days=1)
    todays = (await db.execute(
        select(Fortune).where(
            Fortune.user_id == user.id,
            Fortune.created_at >= today_start,
            Fortune.created_at < tomorrow_start,
        )
    )).scalar_one_or_none()

    schema = _user_to_schema(user)
    return UserMeProfile(
        **schema.model_dump(),
        total_draws=total_draws,
        has_drawn_today=todays is not None,
        todays_fortune=todays.value if todays else None,
    )


@router.get("/me", response_model=dict)
@limiter_decorator("100/minute")
async def read_users_me(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_pk = int(current_user.id)
    user = (await db.execute(select(User).where(User.id == user_pk))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.last_active_date = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    profile = await _build_me_profile(db, user)
    data = {"user": profile}
    if profile.has_drawn_today:
        data["next_draw_at"] = get_next_day_start_in_utc()
    return data


@router.patch("/me", response_model=dict)
@limiter_decorator("20/minute")
async def update_user_me(
    request: Request,
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user_pk = int(current_user.id)
    user = (await db.execute(select(User).where(User.id == user_pk))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    for k, v in update_data.items():
        setattr(user, k, v)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Display name is already taken. Please choose another one.")

    await db.refresh(user)
    profile = await _build_me_profile(db, user)
    data = {"user": profile}
    if profile.has_drawn_today:
        data["next_draw_at"] = get_next_day_start_in_utc()
    return data


@router.patch("/me/password", status_code=200, response_model=dict)
@limiter_decorator("5/minute")
async def update_user_password(
    request: Request,
    password_update: PasswordUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user_pk = int(current_user.id)
    user = (await db.execute(select(User).where(User.id == user_pk))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(password_update.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password.")

    new_hash = get_password_hash(password_update.new_password)
    now = datetime.now(timezone.utc)
    boundary = now.replace(microsecond=0) + timedelta(seconds=1)

    user.password_hash = new_hash
    user.password_changed_at = boundary
    await db.commit()

    new_token = create_access_token(
        data={"sub": current_user.id},
        issued_at=boundary,
    )
    return {
        "message": "Password updated successfully.",
        "access_token": new_token,
        "token_type": "bearer",
    }


@router.get("/me/export", response_model=dict)
@limiter_decorator("5/minute")
async def export_user_data(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user_pk = int(current_user.id)
    user = (await db.execute(select(User).where(User.id == user_pk))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    history = (await db.execute(
        select(Fortune).where(Fortune.user_id == user_pk).order_by(Fortune.created_at.asc())
    )).scalars().all()

    user_dict = {
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "status": user.status,
        "is_hidden": user.is_hidden,
        "tags": user.tags or [],
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "background_url": user.background_url,
        "language": user.language,
        "timezone": user.timezone,
        "registration_date": user.registration_date.isoformat() if user.registration_date else None,
        "last_active_date": user.last_active_date.isoformat() if user.last_active_date else None,
        "qq": user.qq,
        "use_qq_avatar": user.use_qq_avatar,
    }
    fortune_history = [
        {"date": f.created_at.isoformat(), "value": f.value} for f in history
    ]
    return {"user_profile": user_dict, "fortune_history": fortune_history}


@router.get("/u/{username}/fortune-history", response_model=list[FortuneHistoryItem])
@limiter_decorator("60/minute")
async def get_user_fortune_history(
    request: Request,
    username: str,
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(
        select(User).where(User.username == username.lower())
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    rows = (await db.execute(
        select(Fortune).where(
            Fortune.user_id == user.id,
            Fortune.created_at >= one_year_ago,
        )
    )).scalars().all()

    return [FortuneHistoryItem(created_at=r.created_at, value=r.value) for r in rows]


@router.get("/u/{username}", response_model=UserPublicProfile)
@limiter_decorator("60/minute")
async def get_public_profile(
    request: Request,
    username: str,
    db: AsyncSession = Depends(get_db),
    requester: UserInDB | None = Depends(get_optional_current_user),
):
    user = (await db.execute(
        select(User).where(User.username == username.lower())
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_hidden = user.is_hidden
    is_requester_admin = requester and requester.role == "admin"
    if is_hidden and not is_requester_admin:
        raise HTTPException(status_code=404, detail="User not found")

    total_draws = (await db.execute(
        select(func.count()).select_from(Fortune).where(Fortune.user_id == user.id)
    )).scalar_one()

    today_start = get_current_day_start_in_utc()
    tomorrow_start = today_start + timedelta(days=1)
    todays = (await db.execute(
        select(Fortune).where(
            Fortune.user_id == user.id,
            Fortune.created_at >= today_start,
            Fortune.created_at < tomorrow_start,
        )
    )).scalar_one_or_none()

    use_qq = user.use_qq_avatar
    qq_to_return = user.qq if use_qq and user.qq else None

    return UserPublicProfile(
        username=user.username,
        display_name=user.display_name,
        status=user.status,
        is_hidden=is_hidden,
        tags=user.tags or [],
        bio=user.bio,
        avatar_url=user.avatar_url,
        background_url=user.background_url,
        registration_date=user.registration_date,
        last_active_date=user.last_active_date,
        total_draws=total_draws,
        has_drawn_today=todays is not None,
        todays_fortune=todays.value if todays else None,
        qq=qq_to_return,
        use_qq_avatar=use_qq,
    )


@router.get("/u/{username}/qq-public-status", response_model=dict)
@limiter_decorator("100/minute")
async def check_user_qq_publicity(
    request: Request,
    username: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = (await db.execute(
        select(User).where(User.username == username.lower())
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    is_public = bool(target.use_qq_avatar and target.qq is not None)
    return {"is_qq_public": is_public}
