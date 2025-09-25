from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
from datetime import datetime
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
        "display_name": user.username,  # <-- NEW: Set initial display_name
        "email": user.email.lower(),
        "password_hash": hashed_password,
        "role": "user",
        "status": "active",
        "bio": "",
        "avatar_url": "",
        "background_url": "",
        "language": "zh",
        "registration_date": datetime.utcnow(),
        "last_active_date": datetime.utcnow()
    }
    try:
        result = await db.users.insert_one(user_doc)
        new_user_id = result.inserted_id
    except DuplicateKeyError as e:
        if 'username_unique' in e.details['errmsg']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="UserID already exists.")
        if 'email_unique' in e.details['errmsg']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists.")
        # NEW: Handle display_name conflict on registration (rare but possible)
        if 'display_name_unique' in e.details['errmsg']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Display name already exists.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A registration conflict occurred.")

    created_user_doc = await db.users.find_one({"_id": new_user_id})
    access_token = create_access_token(data={"sub": str(new_user_id)})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": UserMeProfile(**created_user_doc, id=str(created_user_doc["_id"]), total_draws=0)
    }

# The /login route does not need changes as it already fetches and returns the full user document.
# ... (Keep the /login route as it is)
@router.post("/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncIOMotorDatabase = Depends(get_db)):
    user_doc = await db.users.find_one({"username": form_data.username.lower()})
    if not user_doc or not verify_password(form_data.password, user_doc["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    await db.users.update_one({"_id": user_doc["_id"]}, {"$set": {"last_active_date": datetime.utcnow()}})
    access_token = create_access_token(data={"sub": str(user_doc["_id"])})
    total_draws = await db.fortunes.count_documents({"user_id": user_doc["_id"]})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": UserMeProfile(**user_doc, id=str(user_doc["_id"]), total_draws=total_draws)
    }