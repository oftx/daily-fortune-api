# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone, timedelta

from ..core.security import create_access_token, get_password_hash, verify_password
from ..db import get_db
from ..models.user import UserCreate, UserMeProfile
from ..models.token import Token
from ..core.rate_limiter import limiter_decorator
from ..core.time_service import get_current_day_start_in_utc
from ..core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter_decorator("5/minute")
async def register_user(request: Request, user: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
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
        "last_active_date": datetime.now(timezone.utc),
        "is_hidden": False,
        "tags": [],
        "timezone": settings.USER_DEFAULT_TIMEZONE
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
    
    created_user_doc['_id'] = str(created_user_doc['_id'])
    
    is_hidden_status = created_user_doc.pop("is_hidden", False)
    tags_list = created_user_doc.pop("tags", [])

    user_profile = UserMeProfile(
        **created_user_doc,
        id=str(new_user_id),
        total_draws=0,
        has_drawn_today=False,
        todays_fortune=None,
        is_hidden=is_hidden_status,
        tags=tags_list
    )

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user_profile
    }

@router.post("/login")
@limiter_decorator("10/minute")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncIOMotorDatabase = Depends(get_db)):
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
    
    today_start_utc = get_current_day_start_in_utc()
    tomorrow_start_utc = today_start_utc + timedelta(days=1)
    
    todays_fortune_doc = await db.fortunes.find_one({
        "user_id": user_id_obj,
        "created_at": {
            "$gte": today_start_utc,
            "$lt": tomorrow_start_utc
        }
    })
    
    has_drawn_today = todays_fortune_doc is not None
    todays_fortune_value = todays_fortune_doc.get("value") if todays_fortune_doc else None
    
    is_hidden_status = user_doc.pop("is_hidden", False)
    tags_list = user_doc.pop("tags", [])
    
    user_doc['_id'] = str(user_doc['_id'])

    # --- THIS IS THE FIX ---
    # The `**user_doc` already passes the 'timezone' key.
    # The explicit `timezone=` argument was redundant and caused the TypeError.
    # It has been removed.
    user_profile = UserMeProfile(
        **user_doc, 
        id=str(user_id_obj), 
        total_draws=total_draws, 
        has_drawn_today=has_drawn_today,
        todays_fortune=todays_fortune_value,
        is_hidden=is_hidden_status,
        tags=tags_list
    )
    # --- END OF FIX ---

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user_profile
    }