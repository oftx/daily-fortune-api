# app/models/user.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserInDB(UserBase):
    id: str = Field(alias="_id")
    display_name: str
    password_hash: str
    role: str = "user"
    status: str = "active"
    is_hidden: bool = False
    tags: List[str] = Field(default_factory=list)
    bio: str = ""
    avatar_url: str = ""
    background_url: str = ""
    language: str = "zh"
    registration_date: datetime = Field(default_factory=datetime.utcnow)
    last_active_date: datetime = Field(default_factory=datetime.utcnow)

class UserPublicProfile(BaseModel):
    username: str
    display_name: str
    bio: str
    avatar_url: str
    background_url: str
    registration_date: datetime
    last_active_date: datetime
    total_draws: int
    has_drawn_today: bool
    todays_fortune: Optional[str] = None
    status: str
    is_hidden: bool
    tags: List[str]

class UserMeProfile(UserPublicProfile):
    id: str
    email: EmailStr
    role: str
    language: str

class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=3, max_length=50)
    bio: Optional[str] = Field(None, max_length=300)
    avatar_url: Optional[str] = Field(None)
    background_url: Optional[str] = Field(None)
    language: Optional[str] = Field(None, pattern="^(zh|en)$")