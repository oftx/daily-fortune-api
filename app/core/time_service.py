# app/core/time_service.py

from datetime import datetime, time, timedelta, timezone
import pytz
from .config import settings

def get_current_day_start_in_utc() -> datetime:
    """
    Calculates the exact start datetime of the "current business day" in UTC.
    This logic is based on the configured APP_TIMEZONE and DAY_RESET_OFFSET_SECONDS.
    
    The returned datetime is always timezone-aware and in UTC.
    """
    try:
        # Get the target timezone from settings
        app_tz = pytz.timezone(settings.APP_TIMEZONE)
    except pytz.UnknownTimeZoneError:
        # Fallback to UTC if the timezone is invalid
        app_tz = pytz.utc

    # Get the current time in the target timezone
    now_in_app_tz = datetime.now(app_tz)

    # Apply the offset to determine the "logical" current time
    logical_now = now_in_app_tz - timedelta(seconds=settings.DAY_RESET_OFFSET_SECONDS)
    
    # The start of the "logical day" is the date part of the logical time
    logical_day_date = logical_now.date()
    
    # The start of the "logical day" in the app's timezone is at midnight of that date
    day_start_naive = datetime.combine(logical_day_date, time.min)
    
    # Make it timezone-aware
    day_start_in_app_tz = app_tz.localize(day_start_naive)
    
    # Now, add the offset back to get the actual reset time
    actual_day_reset_time_in_app_tz = day_start_in_app_tz + timedelta(seconds=settings.DAY_RESET_OFFSET_SECONDS)

    # Finally, convert this start time back to UTC for database storage and comparison
    day_start_utc = actual_day_reset_time_in_app_tz.astimezone(pytz.utc)

    return day_start_utc