import logging
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import oauth2_scheme, jwt, settings
from ..db import get_db
from ..models.token import TokenData
from ..models.user import UserInDB
from ..models.db_models import User

logger = logging.getLogger("api_logger")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def _user_to_schema(u: User) -> UserInDB:
    return UserInDB(
        id=str(u.id),
        username=u.username,
        email=u.email,
        display_name=u.display_name,
        password_hash=u.password_hash,
        role=u.role,
        status=u.status,
        is_hidden=u.is_hidden,
        tags=u.tags or [],
        bio=u.bio or "",
        avatar_url=u.avatar_url or "",
        background_url=u.background_url or "",
        language=u.language,
        timezone=u.timezone,
        registration_date=u.registration_date,
        last_active_date=u.last_active_date,
        qq=u.qq,
        use_qq_avatar=u.use_qq_avatar,
        password_changed_at=u.password_changed_at,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserInDB:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        issued_at_ts = payload.get("iat")
        if user_id is None or issued_at_ts is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception

    try:
        user_pk = int(token_data.user_id)
    except (TypeError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_pk))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    if user.password_changed_at:
        token_issued_at_dt = datetime.fromtimestamp(issued_at_ts, tz=timezone.utc)
        pwd_changed = user.password_changed_at
        if pwd_changed.tzinfo is None:
            pwd_changed = pwd_changed.replace(tzinfo=timezone.utc)
        if token_issued_at_dt < pwd_changed:
            raise credentials_exception

    return _user_to_schema(user)


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Read-only access.",
        )
    return current_user


async def get_optional_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserInDB | None:
    if token is None:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None
