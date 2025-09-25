# app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta

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
    total_draws = await db.fortunes.count_documents({"user_id": ObjectId(current_user.id)})
    
    user_data = current_user.dict()
    user_data["total_draws"] = total_draws
    
    return UserMeProfile(**user_data)

@router.patch("/me", response_model=UserMeProfile)
async def update_user_me(
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    user_id_obj = ObjectId(current_user.id)
    
    # Get update data, excluding fields that were not set in the request
    update_data = user_update.dict(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    await db.users.update_one(
        {"_id": user_id_obj},
        {"$set": update_data}
    )
    
    # Fetch the updated user data to return
    updated_user_doc = await db.users.find_one({"_id": user_id_obj})
    total_draws = await db.fortunes.count_documents({"user_id": user_id_obj})
    
    return UserMeProfile(**updated_user_doc, id=str(updated_user_doc["_id"]), total_draws=total_draws)


@router.get("/@{username}/fortune-history", response_model=list[FortuneHistoryItem])
async def get_user_fortune_history(username: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db.users.find_one({"username": username.lower()})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    one_year_ago = datetime.utcnow() - timedelta(days=365)
    
    history_cursor = db.fortunes.find({
        "user_id": user["_id"],
        "date": {"$gte": one_year_ago}
    })
    
    history = []
    async for record in history_cursor:
        history.append(FortuneHistoryItem(date=record["date"].date(), value=record["value"]))
        
    return history


@router.get("/@{username}", response_model=UserPublicProfile)
async def get_public_profile(username: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    user_doc = await db.users.find_one({"username": username.lower()})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    total_draws = await db.fortunes.count_documents({"user_id": user_doc["_id"]})
    
    user_data = {**user_doc, "total_draws": total_draws}
    
    return UserPublicProfile(**user_data)