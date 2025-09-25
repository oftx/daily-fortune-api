# app/routers/fortune.py

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, date, time, timezone
from bson import ObjectId
from typing import List

from ..db import get_db
from ..services.fortune_service import draw_fortune_logic, FORTUNE_RANKS
from ..models.user import UserInDB
from ..models.fortune import LeaderboardGroup
from .dependencies import get_optional_current_user
from ..core.rate_limiter import limiter_decorator
from ..core.time_service import get_current_day_start_in_utc

router = APIRouter(prefix="/fortune", tags=["Fortune"])

@router.post("/draw")
@limiter_decorator("30/minute")
async def draw(request: Request, db: AsyncIOMotorDatabase = Depends(get_db), current_user: UserInDB | None = Depends(get_optional_current_user)):
    
    if current_user:
        if current_user.status != "active":
            raise HTTPException(status_code=403, detail="Account is deactivated. Cannot draw.")

        user_id_obj = ObjectId(current_user.id)
        
        await db.users.update_one({"_id": user_id_obj}, {"$set": {"last_active_date": datetime.now(timezone.utc)}})
        
        today_start_utc = get_current_day_start_in_utc()
        existing_fortune = await db.fortunes.find_one({
            "user_id": user_id_obj,
            "date": today_start_utc
        })
        
        if existing_fortune:
            return {"fortune": existing_fortune["value"]}

        new_fortune_value = draw_fortune_logic()
        fortune_doc = {
            "user_id": user_id_obj,
            "date": today_start_utc,
            "value": new_fortune_value,
            "created_at": datetime.now(timezone.utc)
        }
        await db.fortunes.insert_one(fortune_doc)
        return {"fortune": new_fortune_value}
    else:
        return {"fortune": draw_fortune_logic()}

@router.get("/leaderboard", response_model=List[LeaderboardGroup])
@limiter_decorator("60/minute")
async def get_todays_leaderboard(request: Request, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Gets the leaderboard for fortunes drawn today, grouped and sorted by fortune rank.
    """
    today_start_utc = get_current_day_start_in_utc()

    # --- MODIFICATION: Rewritten aggregation pipeline ---
    pipeline = [
        # 1. Find today's fortunes
        {
            "$match": { "date": {"$eq": today_start_utc} }
        },
        # 2. Join with users collection
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_info"
            }
        },
        # 3. Deconstruct the user_info array
        {
            "$unwind": "$user_info"
        },
        # 4. Group by fortune value
        {
            "$group": {
                "_id": "$value",
                "users": {
                    "$push": {
                        "username": "$user_info.username",
                        "display_name": "$user_info.display_name"
                    }
                }
            }
        },
        # 5. Reshape the document
        {
            "$project": {
                "_id": 0,
                "fortune": "$_id",
                "users": 1
            }
        }
    ]
    # --- END OF MODIFICATION ---
    
    leaderboard_cursor = db.fortunes.aggregate(pipeline)
    leaderboard_data = await leaderboard_cursor.to_list(length=None)
    
    # --- NEW: Sort in Python using the defined ranks ---
    # This is simpler and more maintainable than a complex aggregation $switch
    leaderboard_data.sort(key=lambda item: FORTUNE_RANKS.get(item['fortune'], 0), reverse=True)
    
    return [LeaderboardGroup(**item) for item in leaderboard_data]