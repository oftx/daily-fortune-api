# app/models/fortune.py

from pydantic import BaseModel
from datetime import date

class FortuneHistoryItem(BaseModel):
    date: date
    value: str

class LeaderboardEntry(BaseModel):
    username: str      # The unique UserID for the link
    display_name: str  # The name to show to the user
    value: str