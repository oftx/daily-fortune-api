# /daily-fortune-api/app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta, timezone
import pytz

from ..db import get_db
from ..models.user import UserInDB, UserMeProfile, UserPublicProfile, UserUpdate, PasswordUpdate
from ..models.fortune import FortuneHistoryItem
from .dependencies import get_current_user, get_current_active_user, get_optional_current_user
from bson import ObjectId
from ..core.rate_limiter import limiter_decorator
from ..core.time_service import get_current_day_start_in_utc, get_next_day_start_in_utc
from ..core.config import settings
from ..core.security import verify_password, get_password_hash, create_access_token
from pymongo.errors import DuplicateKeyError

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=dict)
@limiter_decorator("100/minute")
async def read_users_me(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    user_id_obj = ObjectId(current_user.id)
    
    await db.users.update_one(
        {"_id": user_id_obj},
        {"$set": {"last_active_date": datetime.now(timezone.utc)}}
    )

    total_draws = await db.fortunes.count_documents({"user_id": user_id_obj})
    
    today_start_utc = get_current_day_start_in_utc()
    tomorrow_start_utc = today_start_utc + timedelta(days=1)
    
    todays_fortune_doc = await db.fortunes.find_one({
        "user_id": user_id_obj,
        "created_at": { "$gte": today_start_utc, "$lt": tomorrow_start_utc }
    })
    
    has_drawn_today = todays_fortune_doc is not None
    todays_fortune_value = todays_fortune_doc.get("value") if todays_fortune_doc else None
    
    user_profile = UserMeProfile(
        **current_user.model_dump(),
        total_draws=total_draws,
        has_drawn_today=has_drawn_today,
        todays_fortune=todays_fortune_value
    )
    
    response_data = {"user": user_profile}
    
    if has_drawn_today:
        response_data["next_draw_at"] = get_next_day_start_in_utc()
    
    return response_data

@router.patch("/me", response_model=dict)
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
        "qq": updated_user_doc.get("qq"),
        "use_qq_avatar": updated_user_doc.get("use_qq_avatar", False)
    }
    user_profile = UserMeProfile(**user_profile_data)
    
    response_data = {"user": user_profile}

    if has_drawn_today:
        response_data["next_draw_at"] = get_next_day_start_in_utc()

    return response_data


@router.patch("/me/password", status_code=status.HTTP_200_OK, response_model=dict)
@limiter_decorator("5/minute")
async def update_user_password(
    request: Request,
    password_update: PasswordUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    user_id_obj = ObjectId(current_user.id)
    
    if not verify_password(password_update.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password."
        )
        
    new_password_hash = get_password_hash(password_update.new_password)
    
    # --- FINAL FIX for Password Change Invalidation ---
    # We create a definitive invalidation boundary at the beginning of the NEXT second.
    # This guarantees that any token issued in the current second (or before)
    # will have an `iat` that is strictly less than this boundary.
    now = datetime.now(timezone.utc)
    invalidation_boundary = now.replace(microsecond=0) + timedelta(seconds=1)

    await db.users.update_one(
        {"_id": user_id_obj},
        {"$set": {
            "password_hash": new_password_hash,
            "password_changed_at": invalidation_boundary
        }}
    )
    
    # Issue the new token aligned exactly with this boundary, so it won't be self-invalidated.
    new_access_token = create_access_token(
        data={"sub": current_user.id},
        issued_at=invalidation_boundary
    )
    
    return {
        "message": "Password updated successfully.",
        "access_token": new_access_token,
        "token_type": "bearer"
    }


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
    
    history = [FortuneHistoryItem(**record) async for record in history_cursor]
        
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

    use_qq = user_doc.get("use_qq_avatar", False)
    user_qq_number = user_doc.get("qq")
    qq_to_return = user_qq_number if use_qq and user_qq_number else None

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
        "qq": qq_to_return,
        "use_qq_avatar": use_qq,
    }
    
    return UserPublicProfile(**user_profile_data)

@router.get("/u/{username}/qq-public-status", response_model=dict)
@limiter_decorator("100/minute")
async def check_user_qq_publicity(
    request: Request,
    username: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    target_user_doc = await db.users.find_one({"username": username.lower()})
    
    if not target_user_doc:
        raise HTTPException(status_code=404, detail="User not found")
        
    is_public = target_user_doc.get("use_qq_avatar", False) and target_user_doc.get("qq") is not None
    
    return {"is_qq_public": is_public}