# main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import IndexModel, ASCENDING
from pymongo.errors import OperationFailure
from contextlib import asynccontextmanager
import logging
from logging.handlers import RotatingFileHandler
import time
from jose import jwt, JWTError

# --- MODIFIED: Import both limiter and limiter_decorator ---
from app.core.rate_limiter import limiter, limiter_decorator
from app.core.config import settings

# --- Import the exception only if the limiter is active ---
if limiter:
    from slowapi.errors import RateLimitExceeded

from app.db import db
from app.routers import auth, config, fortune, users, admin


logger = logging.getLogger("api_logger")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("api.log", maxBytes=5*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: creating database indexes...")
    try:
        await db.users.create_indexes([
            IndexModel([("username", ASCENDING)], unique=True, name="username_unique"),
            IndexModel([("email", ASCENDING)], unique=True, name="email_unique"),
            IndexModel([("display_name", ASCENDING)], unique=True, name="display_name_unique", collation={'locale': 'en', 'strength': 2})
        ])
        await db.fortunes.create_indexes([
            IndexModel([("user_id", ASCENDING)], name="fortune_user_id"),
            IndexModel([("user_id", ASCENDING), ("date", ASCENDING)], unique=True, name="user_date_unique")
        ])
        await db.config.create_indexes([
            IndexModel([("key", ASCENDING)], unique=True, name="config_key_unique")
        ])
        logger.info("Database indexes created successfully.")
    except OperationFailure as e:
        logger.error(f"An error occurred during index creation: {e}")
    yield
    logger.info("Application shutdown.")


app = FastAPI(
    title="DailyFortune API",
    description="Backend API for the DailyFortune React application.",
    version="1.0.0",
    lifespan=lifespan
)


if settings.RATE_LIMITING_ENABLED and limiter:
    logger.info(f"Rate limiting is ENABLED. Storage: {settings.REDIS_URL}")
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
        logger.warning(f"Rate limit exceeded for IP {request.client.host} on path {request.url.path}")
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded: {exc.detail}"},
        )
else:
    logger.info("Rate limiting is DISABLED.")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    user_id = "anonymous"
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub", "unknown")
        except JWTError:
            user_id = "invalid_token"

    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    ip_address = request.client.host
    
    log_message = (
        f'user="{user_id}" '
        f'ip="{ip_address}" '
        f'method="{request.method}" '
        f'path="{request.url.path}" '
        f'status={response.status_code} '
        f'duration={process_time:.2f}ms'
    )
    logger.info(log_message)
    return response


origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(config.router)
app.include_router(fortune.router)
app.include_router(users.router)
app.include_router(admin.router)

@app.get("/")
@limiter_decorator("100/minute") # Example of applying a general limit
def read_root(request: Request):
    return {"message": "Welcome to the DailyFortune API!"}