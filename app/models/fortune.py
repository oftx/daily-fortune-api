# app/models/fortune.py

from pydantic import BaseModel
from datetime import date, datetime
from typing import List

class FortuneHistoryItem(BaseModel):
    created_at: datetime
    value: str

class LeaderboardUser(BaseModel):
    username: str
    display_name: str

class LeaderboardGroup(BaseModel):
    fortune: str
    users: List[LeaderboardUser]