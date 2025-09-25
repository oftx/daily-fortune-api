# app/routers/admin.py

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from ..db import get_db
from ..models.user import UserInDB, UserMeProfile
from .dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["Administration"])

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
    
    # We can reuse the UserMeProfile model, but we need to count draws for each user
    user_profiles = []
    for user in users:
        user_id_obj = user["_id"]
        total_draws = await db.fortunes.count_documents({"user_id": user_id_obj})
        
        user_profile_data = {
            **user,
            "id": str(user_id_obj),
            "total_draws": total_draws,
        }
        user_profiles.append(UserMeProfile(**user_profile_data))
        
    return user_profiles