# app/models/fortune.py

from pydantic import BaseModel
from datetime import date

class FortuneHistoryItem(BaseModel):
    date: date
    value: str

class LeaderboardEntry(BaseModel):
    username: str
    value: str