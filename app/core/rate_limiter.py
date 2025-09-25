# app/core/rate_limiter.py

from slowapi import Limiter
from slowapi.util import get_remote_address
from ..core.config import settings

# This is a dummy decorator that does nothing.
# It's used when rate limiting is disabled in the config.
def no_op_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

# --- Initialize the Limiter only if the feature is enabled ---
if settings.RATE_LIMITING_ENABLED:
    # The key_func determines how to identify a client (by IP address).
    limiter = Limiter(
        key_func=get_remote_address,
        # --- MODIFICATION: Remove storage_options and let slowapi handle the connection ---
        storage_uri=settings.REDIS_URL
    )
    
    # When enabled, our decorator is the real limiter.
    limiter_decorator = limiter.limit
else:
    # When disabled, assign the limiter variable to None and the decorator to our dummy function.
    limiter = None
    limiter_decorator = no_op_decorator