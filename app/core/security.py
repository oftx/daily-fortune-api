# /daily-fortune-api/app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .config import settings
from ..models.token import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# --- FIX: 修改函数签名以接受可选的 issued_at 参数 ---
def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None,
    issued_at: Optional[datetime] = None
) -> str:
    to_encode = data.copy()
    
    # --- FIX: 如果没有提供 issued_at，则使用当前时间 ---
    now = issued_at if issued_at is not None else datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({
        "exp": expire,
        "iat": now
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None,
    issued_at: Optional[datetime] = None
) -> str:
    to_encode = data.copy()
    
    now = issued_at if issued_at is not None else datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt