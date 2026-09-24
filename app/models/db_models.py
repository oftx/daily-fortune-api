from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, JSON,
    ForeignKey, UniqueConstraint, func,
)
from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)
    status = Column(String(20), default="active", nullable=False)
    is_hidden = Column(Boolean, default=False, nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    bio = Column(String(300), default="", nullable=False)
    avatar_url = Column(String(500), default="", nullable=False)
    background_url = Column(String(500), default="", nullable=False)
    language = Column(String(5), default="zh", nullable=False)
    timezone = Column(String(50), nullable=False)
    registration_date = Column(DateTime, server_default=func.now(), nullable=False)
    last_active_date = Column(DateTime, server_default=func.now(), nullable=False)
    qq = Column(Integer, nullable=True)
    use_qq_avatar = Column(Boolean, default=False, nullable=False)
    password_changed_at = Column(DateTime, nullable=True)


class Fortune(Base):
    __tablename__ = "fortunes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    value = Column(String(20), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="user_date_unique"),
    )


class AppConfig(Base):
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
