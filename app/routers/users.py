# app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta, timezone
import pytz

from ..db import get_db
from ..models.user import UserInDB, UserMeProfile, UserPublicProfile, UserUpdate
from ..models.fortune import FortuneHistoryItem
from .dependencies import get_current_user, get_current_active_user, get_optional_current_user
from bson import ObjectId
from ..core.rate_limiter import limiter_decorator
from ..core.time_service import get_current_day_start_in_utc
from ..core.config import settings

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserMeProfile)
@limiter_decorator("100/minute")
async def read_users_me(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    user_id_obj = ObjectId(current_user.id)
    total_draws = await db.fortunes.count_documents({"user_id": user_id_obj})
    
    today_start_utc = get_current_day_start_in_utc()
    tomorrow_start_utc = today_start_utc + timedelta(days=1)
    
    todays_fortune_doc = await db.fortunes.find_one({
        "user_id": user_id_obj,
        "created_at": { "$gte": today_start_utc, "$lt": tomorrow_start_utc }
    })
    
    has_drawn_today = todays_fortune_doc is not None
    todays_fortune_value = todays_fortune_doc.get("value") if todays_fortune_doc else None
    
    user_data = current_user.model_dump()
    user_data["total_draws"] = total_draws
    user_data["has_drawn_today"] = has_drawn_today
    user_data["todays_fortune"] = todays_fortune_value
    
    return UserMeProfile(**user_data)

@router.patch("/me", response_model=UserMeProfile)
@limiter_decorator("20/minute")
async def update_user_me(
    request: Request,
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    user_id_obj = ObjectId(current_user.id)
    update_data = user_update.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    try:
        await db.users.update_one(
            {"_id": user_id_obj},
            {"$set": update_data}
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Display name is already taken. Please choose another one."
        )
    
    updated_user_doc = await db.users.find_one({"_id": user_id_obj})
    
    total_draws = await db.fortunes.count_documents({"user_id": user_id_obj})
    
    today_start_utc = get_current_day_start_in_utc()
    tomorrow_start_utc = today_start_utc + timedelta(days=1)
    
    todays_fortune_doc = await db.fortunes.find_one({
        "user_id": user_id_obj,
        "created_at": { "$gte": today_start_utc, "$lt": tomorrow_start_utc }
    })

    has_drawn_today = todays_fortune_doc is not None
    todays_fortune_value = todays_fortune_doc.get("value") if todays_fortune_doc else None

    user_profile_data = {
        "id": str(updated_user_doc["_id"]),
        "username": updated_user_doc["username"],
        "display_name": updated_user_doc["display_name"],
        "email": updated_user_doc["email"],
        "role": updated_user_doc["role"],
        "status": updated_user_doc["status"],
        "is_hidden": updated_user_doc.get("is_hidden", False),
        "tags": updated_user_doc.get("tags", []),
        "bio": updated_user_doc["bio"],
        "avatar_url": updated_user_doc["avatar_url"],
        "background_url": updated_user_doc["background_url"],
        "language": updated_user_doc["language"],
        "timezone": updated_user_doc.get("timezone", settings.USER_DEFAULT_TIMEZONE),
        "registration_date": updated_user_doc["registration_date"],
        "last_active_date": updated_user_doc["last_active_date"],
        "total_draws": total_draws,
        "has_drawn_today": has_drawn_today,
        "todays_fortune": todays_fortune_value,
    }

    return UserMeProfile(**user_profile_data)


@router.get("/u/{username}/fortune-history", response_model=list[FortuneHistoryItem])
@limiter_decorator("60/minute")
async def get_user_fortune_history(request: Request, username: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db.users.find_one({"username": username.lower()})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    
    history_cursor = db.fortunes.find({
        "user_id": user["_id"],
        "created_at": {"$gte": one_year_ago}
    })
    
    # --- THIS IS THE FIX ---
    # The logic is now simplified: just pass the raw data to the client.
    # The Pydantic model `FortuneHistoryItem` ensures we only send `created_at` and `value`.
    history = [FortuneHistoryItem(**record) async for record in history_cursor]
    # --- END OF FIX ---
        
    return history


@router.get("/u/{username}", response_model=UserPublicProfile)
@limiter_decorator("60/minute")
async def get_public_profile(
    request: Request,
    username: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    requester: UserInDB | None = Depends(get_optional_current_user)
):
    user_doc = await db.users.find_one({"username": username.lower()})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    is_hidden = user_doc.get("is_hidden", False)
    is_requester_admin = requester and requester.role == "admin"
    
    if is_hidden and not is_requester_admin:
        raise HTTPException(status_code=404, detail="User not found")

    user_id_obj = user_doc["_id"]
    total_draws = await db.fortunes.count_documents({"user_id": user_id_obj})
    
    today_start_utc = get_current_day_start_in_utc()
    tomorrow_start_utc = today_start_utc + timedelta(days=1)
    
    todays_fortune_doc = await db.fortunes.find_one({
        "user_id": user_id_obj,
        "created_at": { "$gte": today_start_utc, "$lt": tomorrow_start_utc }
    })

    has_drawn_today = todays_fortune_doc is not None
    todays_fortune_value = todays_fortune_doc.get("value") if todays_fortune_doc else None

    user_profile_data = {
        "username": user_doc["username"],
        "display_name": user_doc["display_name"],
        "status": user_doc["status"],
        "is_hidden": is_hidden,
        "tags": user_doc.get("tags", []),
        "bio": user_doc["bio"],
        "avatar_url": user_doc["avatar_url"],
        "background_url": user_doc["background_url"],
        "registration_date": user_doc["registration_date"],
        "last_active_date": user_doc["last_active_date"],
        "total_draws": total_draws,
        "has_drawn_today": has_drawn_today,
        "todays_fortune": todays_fortune_value,
    }
    
    return UserPublicProfile(**user_profile_data)