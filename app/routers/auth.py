from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta

from ..core.security import (
    create_access_token, create_refresh_token,
    get_password_hash, verify_password,
)
from ..db import get_db
from ..models.user import UserCreate, UserMeProfile
from ..models.db_models import User, Fortune, AppConfig
from ..core.rate_limiter import limiter_decorator
from ..core.time_service import get_current_day_start_in_utc, get_next_day_start_in_utc
from ..core.config import settings
from ..routers.dependencies import _user_to_schema
from jose import jwt, JWTError

router = APIRouter(prefix="/auth", tags=["Authentication"])


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


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter_decorator("5/minute")
async def register_user(
    request: Request,
    response: Response,
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    cfg = (await db.execute(
        select(AppConfig).where(AppConfig.key == "registration_status")
    )).scalar_one_or_none()
    if not cfg or not cfg.value:
        raise HTTPException(status_code=400, detail="Registration is currently closed.")

    hashed = get_password_hash(user.password)
    now = datetime.now(timezone.utc).replace(microsecond=0)

    new_user = User(
        username=user.username.lower(),
        display_name=user.username,
        email=user.email.lower(),
        password_hash=hashed,
        role="user",
        status="active",
        bio="",
        avatar_url="",
        background_url="",
        language="zh",
        registration_date=now,
        last_active_date=now,
        password_changed_at=now,
        is_hidden=False,
        tags=[],
        timezone=settings.USER_DEFAULT_TIMEZONE,
        qq=None,
        use_qq_avatar=False,
    )
    db.add(new_user)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        msg = str(e.orig).lower()
        if "username" in msg:
            raise HTTPException(status_code=400, detail="UserID already exists.")
        if "email" in msg:
            raise HTTPException(status_code=400, detail="Email already exists.")
        if "display_name" in msg:
            raise HTTPException(status_code=400, detail="Display name already exists.")
        raise HTTPException(status_code=400, detail="A registration conflict occurred.")

    await db.refresh(new_user)

    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})
    profile = await _build_me_profile(db, new_user)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": profile,
    }


@router.post("/login")
@limiter_decorator("10/minute")
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(
        select(User).where(User.username == form_data.username.lower())
    )).scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_active_date = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    profile = await _build_me_profile(db, user)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": profile,
    }


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    cookie = request.cookies.get("refresh_token")
    if not cookie:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        payload = jwt.decode(cookie, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_pk = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user = (await db.execute(select(User).where(User.id == user_pk))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(data={"sub": user_id})
    new_refresh = create_refresh_token(data={"sub": user_id})

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}
