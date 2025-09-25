# app/routers/dependencies.py

from fastapi import Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from jose import JWTError
from bson import ObjectId

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
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"_id": ObjectId(token_data.user_id)})
    if user is None:
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