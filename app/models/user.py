# app/models/user.py

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, value: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise ValueError('Username can only contain letters, numbers, and underscores.')
        return value

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
    timezone: str
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
    timezone: str

class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=3, max_length=50)
    bio: Optional[str] = Field(None, max_length=300)
    avatar_url: Optional[str] = Field(None)
    background_url: Optional[str] = Field(None)
    language: Optional[str] = Field(None, pattern="^(zh|en)$")
    timezone: Optional[str] = Field(None)