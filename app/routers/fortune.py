# app/routers/fortune.py

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, date, time
from bson import ObjectId
from typing import List

from ..db import get_db
from ..services.fortune_service import draw_fortune_logic
from ..models.user import UserInDB
from ..models.fortune import LeaderboardEntry
from .dependencies import get_optional_current_user

router = APIRouter(prefix="/fortune", tags=["Fortune"])

@router.post("/draw")
async def draw(current_user: UserInDB | None = Depends(get_optional_current_user), db: AsyncIOMotorDatabase = Depends(get_db)):
    today = datetime.utcnow().date()
    
    if current_user:
        user_id_obj = ObjectId(current_user.id)
        
        # Update user's last active time on this significant action
        await db.users.update_one({"_id": user_id_obj}, {"$set": {"last_active_date": datetime.utcnow()}})
        
        today_start = datetime.combine(today, time.min)
        existing_fortune = await db.fortunes.find_one({
            "user_id": user_id_obj,
            "date": today_start
        })
        
        if existing_fortune:
            return {"fortune": existing_fortune["value"]}

        new_fortune_value = draw_fortune_logic()
        fortune_doc = {
            "user_id": user_id_obj,
            "date": today_start,
            "value": new_fortune_value,
            "created_at": datetime.utcnow()
        }
        await db.fortunes.insert_one(fortune_doc)
        return {"fortune": new_fortune_value}
    else:
        return {"fortune": draw_fortune_logic()}

@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_todays_leaderboard(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Gets the leaderboard for fortunes drawn today.
    This uses a MongoDB aggregation pipeline to join fortunes with users.
    """
    today_start = datetime.combine(datetime.utcnow().date(), time.min)

    pipeline = [
        # 1. Filter for fortunes drawn today
        {
            "$match": {
                "date": {"$gte": today_start}
            }
        },
        # 2. Join with the users collection to get username
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_info"
            }
        },
        # 3. Deconstruct the user_info array field from the lookup
        {
            "$unwind": "$user_info"
        },
        # 4. Project the final fields
        {
            "$project": {
                "_id": 0,
                "username": "$user_info.username",
                "value": "$value"
            }
        }
    ]
    
    leaderboard_cursor = db.fortunes.aggregate(pipeline)
    leaderboard_data = await leaderboard_cursor.to_list(length=None)
    
    return [LeaderboardEntry(**item) for item in leaderboard_data]