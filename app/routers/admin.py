# app/routers/admin.py

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from datetime import datetime, time, timezone
from pydantic import BaseModel
from bson import ObjectId

from ..db import get_db
from ..models.user import UserInDB, UserMeProfile
from .dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["Administration"])

class StatusUpdate(BaseModel):
    status: str

class VisibilityUpdate(BaseModel):
    is_hidden: bool

class TagsUpdate(BaseModel):
    tags: List[str]

# Dependency to check for admin role
async def get_current_admin_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

@router.get("/users", response_model=List[UserMeProfile])
async def read_all_users(
    admin_user: UserInDB = Depends(get_current_admin_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get a list of all users. Requires admin privileges.
    """
    users_cursor = db.users.find()
    users = await users_cursor.to_list(length=None)
    
    user_profiles = []
    today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min)
    
    for user in users:
        user_id_obj = user["_id"]
        total_draws = await db.fortunes.count_documents({"user_id": user_id_obj})
        
        todays_fortune_doc = await db.fortunes.find_one({
            "user_id": user_id_obj,
            "date": today_start
        })

        has_drawn_today = todays_fortune_doc is not None
        todays_fortune_value = todays_fortune_doc.get("value") if todays_fortune_doc else None

        user_profile_data = {
            **user,
            "id": str(user_id_obj),
            "total_draws": total_draws,
            "has_drawn_today": has_drawn_today,
            "todays_fortune": todays_fortune_value,
            "is_hidden": user.get("is_hidden", False),
            "tags": user.get("tags", [])
        }
        user_profiles.append(UserMeProfile(**user_profile_data))
        
    return user_profiles

@router.post("/users/{user_id}/status", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_status(
    user_id: str,
    status_update: StatusUpdate,
    admin_user: UserInDB = Depends(get_current_admin_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if status_update.status not in ["active", "inactive"]:
        raise HTTPException(status_code=400, detail="Invalid status value")
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"status": status_update.status}}
    )
    return

@router.post("/users/{user_id}/visibility", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_visibility(
    user_id: str,
    visibility_update: VisibilityUpdate,
    admin_user: UserInDB = Depends(get_current_admin_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_hidden": visibility_update.is_hidden}}
    )
    return

@router.post("/users/{user_id}/tags", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_tags(
    user_id: str,
    tags_update: TagsUpdate,
    admin_user: UserInDB = Depends(get_current_admin_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"tags": tags_update.tags}}
    )
    return