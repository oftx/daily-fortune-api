from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
from datetime import datetime
from bson import ObjectId

from ..core.security import create_access_token, get_password_hash, verify_password
from ..db import get_db
from ..models.user import UserCreate, UserInDB
from ..models.token import Token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    config = await db.config.find_one({"key": "registration_status"})
    if not config or not config.get("value", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration is currently closed.")

    hashed_password = get_password_hash(user.password)
    user_doc = {
        "username": user.username.lower(),
        "email": user.email.lower(),
        "password_hash": hashed_password,
        "role": "user",
        "status": "active",
        "bio": "",
        "avatar_url": "",
        "background_url": "",
        "language": "zh",
        "registration_date": datetime.utcnow(),
        "last_active_date": datetime.utcnow()
    }
    try:
        new_user = await db.users.insert_one(user_doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists.")

    access_token = create_access_token(data={"sub": str(new_user.inserted_id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db.users.find_one({"username": form_data.username.lower()})
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last active date
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"last_active_date": datetime.utcnow()}})
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    return {"access_token": access_token, "token_type": "bearer"}
