from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone, time # <-- IMPORT time
from bson import ObjectId

from ..core.security import create_access_token, get_password_hash, verify_password
from ..db import get_db
from ..models.user import UserCreate, UserMeProfile
from ..models.token import Token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    config = await db.config.find_one({"key": "registration_status"})
    if not config or not config.get("value", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration is currently closed.")

    hashed_password = get_password_hash(user.password)
    user_doc = {
        "username": user.username.lower(),
        "display_name": user.username,
        "email": user.email.lower(),
        "password_hash": hashed_password,
        "role": "user",
        "status": "active",
        "bio": "",
        "avatar_url": "",
        "background_url": "",
        "language": "zh",
        "registration_date": datetime.now(timezone.utc),
        "last_active_date": datetime.now(timezone.utc)
    }
    try:
        result = await db.users.insert_one(user_doc)
        new_user_id = result.inserted_id
    except DuplicateKeyError as e:
        if 'username_unique' in e.details['errmsg']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="UserID already exists.")
        if 'email_unique' in e.details['errmsg']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists.")
        if 'display_name_unique' in e.details['errmsg']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Display name already exists.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A registration conflict occurred.")
    
    created_user_doc = await db.users.find_one({"_id": new_user_id})
    access_token = create_access_token(data={"sub": str(new_user_id)})
    
    # For a new user, has_drawn_today is always False
    user_profile = UserMeProfile(**created_user_doc, id=str(created_user_doc["_id"]), total_draws=0, has_drawn_today=False)

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user_profile
    }

@router.post("/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncIOMotorDatabase = Depends(get_db)):
    user_doc = await db.users.find_one({"username": form_data.username.lower()})
    if not user_doc or not verify_password(form_data.password, user_doc["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id_obj = user_doc["_id"]
    await db.users.update_one({"_id": user_id_obj}, {"$set": {"last_active_date": datetime.now(timezone.utc)}})
    
    access_token = create_access_token(data={"sub": str(user_id_obj)})
    total_draws = await db.fortunes.count_documents({"user_id": user_id_obj})
    
    # --- THIS IS THE FIX ---
    # We must calculate has_drawn_today and provide it to the model
    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min)
    todays_fortune = await db.fortunes.find_one({
        "user_id": user_id_obj,
        "date": today_start
    })
    has_drawn_today = todays_fortune is not None
    
    user_profile = UserMeProfile(
        **user_doc, 
        id=str(user_id_obj), 
        total_draws=total_draws, 
        has_drawn_today=has_drawn_today
    )
    # --- END OF FIX ---

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user_profile
    }