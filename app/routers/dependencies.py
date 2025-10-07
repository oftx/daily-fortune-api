# /daily-fortune-api/app/routers/dependencies.py

from fastapi import Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from jose import JWTError
from bson import ObjectId
from datetime import datetime, timezone

from ..core.security import oauth2_scheme, jwt, settings
from ..db import get_db
from ..models.token import TokenData
from ..models.user import UserInDB

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncIOMotorDatabase = Depends(get_db)) -> UserInDB:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        # --- FIX: 从Token中获取 'iat' (issued at) 声明 ---
        issued_at_ts = payload.get("iat")
        if user_id is None or issued_at_ts is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"_id": ObjectId(token_data.user_id)})
    if user is None:
        raise credentials_exception
    
    # --- FIX: 检查Token是否在密码修改前签发 ---
    password_changed_at = user.get("password_changed_at")
    if password_changed_at:
        # 将iat时间戳转换为带时区的datetime对象以便精确比较
        token_issued_at_dt = datetime.fromtimestamp(issued_at_ts, tz=timezone.utc)
        
        # 如果Token的签发时间早于密码最后修改时间，则该Token无效
        if token_issued_at_dt < password_changed_at:
            raise credentials_exception
    
    # --- THE CORRECT FIX ---
    # The UserInDB model has a field `id: str` which is an alias for the input key `_id`.
    # Pydantic expects the value associated with the key `_id` to be a string.
    # Currently, `user['_id']` is an ObjectId. We just need to convert it.
    # We modify the dictionary IN-PLACE before passing it to the model.
    user['_id'] = str(user['_id'])
    # --- END OF FIX ---
    
    return UserInDB(**user)

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if current_user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated. Read-only access.")
    return current_user

# Optional authentication dependency
async def get_optional_current_user(token: str = Depends(oauth2_scheme), db: AsyncIOMotorDatabase = Depends(get_db)) -> UserInDB | None:
    if token is None:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None