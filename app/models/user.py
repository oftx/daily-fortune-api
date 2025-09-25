# app/models/user.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserInDB(UserBase):
    id: str = Field(alias="_id")
    password_hash: str
    role: str = "user"
    status: str = "active"
    bio: str = ""
    avatar_url: str = ""
    background_url: str = ""
    language: str = "zh"
    registration_date: datetime = Field(default_factory=datetime.utcnow)
    last_active_date: datetime = Field(default_factory=datetime.utcnow)

class UserPublicProfile(BaseModel):
    username: str
    bio: str
    avatar_url: str
    background_url: str
    registration_date: datetime
    total_draws: int # <-- ADDED

class UserMeProfile(UserPublicProfile):
    id: str
    email: EmailStr
    role: str
    language: str
    last_active_date: datetime
    # total_draws is inherited

class UserUpdate(BaseModel):
    # Model for updating user settings. All fields are optional.
    bio: Optional[str] = Field(None, max_length=300)
    avatar_url: Optional[str] = Field(None)
    background_url: Optional[str] = Field(None)
    language: Optional[str] = Field(None, pattern="^(zh|en)$") # Example validation