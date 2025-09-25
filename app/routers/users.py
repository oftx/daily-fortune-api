# app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta, time, timezone
from pymongo.errors import DuplicateKeyError

from ..db import get_db
from ..models.user import UserInDB, UserMeProfile, UserPublicProfile, UserUpdate
from ..models.fortune import FortuneHistoryItem
from .dependencies import get_current_user
from bson import ObjectId

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserMeProfile)
async def read_users_me(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    user_id_obj = ObjectId(current_user.id)
    total_draws = await db.fortunes.count_documents({"user_id": user_id_obj})
    
    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min)
    todays_fortune_doc = await db.fortunes.find_one({
        "user_id": user_id_obj,
        "date": today_start
    })
    
    has_drawn_today = todays_fortune_doc is not None
    todays_fortune_value = todays_fortune_doc.get("value") if todays_fortune_doc else None
    
    user_data = current_user.dict()
    user_data["total_draws"] = total_draws
    user_data["has_drawn_today"] = has_drawn_today
    user_data["todays_fortune"] = todays_fortune_value
    
    return UserMeProfile(**user_data)

@router.patch("/me", response_model=UserMeProfile)
async def update_user_me(
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    user_id_obj = ObjectId(current_user.id)
    update_data = user_update.dict(exclude_unset=True)
    
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
    
    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min)
    todays_fortune_doc = await db.fortunes.find_one({
        "user_id": user_id_obj,
        "date": today_start
    })

    has_drawn_today = todays_fortune_doc is not None
    todays_fortune_value = todays_fortune_doc.get("value") if todays_fortune_doc else None

    user_data = {
        **updated_user_doc, 
        "id": str(updated_user_doc["_id"]), 
        "total_draws": total_draws, 
        "has_drawn_today": has_drawn_today,
        "todays_fortune": todays_fortune_value
    }

    return UserMeProfile(**user_data)


@router.get("/u/{username}/fortune-history", response_model=list[FortuneHistoryItem])
async def get_user_fortune_history(username: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db.users.find_one({"username": username.lower()})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    
    history_cursor = db.fortunes.find({
        "user_id": user["_id"],
        "date": {"$gte": one_year_ago}
    })
    
    history = []
    async for record in history_cursor:
        history.append(FortuneHistoryItem(date=record["date"].date(), value=record["value"]))
        
    return history


@router.get("/u/{username}", response_model=UserPublicProfile)
async def get_public_profile(username: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    user_doc = await db.users.find_one({"username": username.lower()})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_id_obj = user_doc["_id"]
    total_draws = await db.fortunes.count_documents({"user_id": user_id_obj})
    
    # --- MODIFICATION START: Fetch fortune status for the public profile ---
    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min)
    todays_fortune_doc = await db.fortunes.find_one({
        "user_id": user_id_obj,
        "date": today_start
    })

    has_drawn_today = todays_fortune_doc is not None
    todays_fortune_value = todays_fortune_doc.get("value") if todays_fortune_doc else None

    user_data = {
        **user_doc, 
        "total_draws": total_draws,
        "has_drawn_today": has_drawn_today,
        "todays_fortune": todays_fortune_value
    }
    # --- MODIFICATION END ---
    
    return UserPublicProfile(**user_data)