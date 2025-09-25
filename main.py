# main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pymongo import IndexModel, ASCENDING
from pymongo.errors import OperationFailure
from contextlib import asynccontextmanager
import logging
from logging.handlers import RotatingFileHandler
import time
from jose import jwt, JWTError

from app.db import db
from app.routers import auth, config, fortune, users, admin
from app.core.config import settings

# --- NEW: LOGGING SETUP ---
# Create a logger instance
logger = logging.getLogger("api_logger")
logger.setLevel(logging.INFO)

# Create a file handler that rotates logs, keeping 5 backups of 5MB each
# This prevents the log file from growing indefinitely
handler = RotatingFileHandler("api.log", maxBytes=5*1024*1024, backupCount=5)

# Create a formatter and add it to the handler
# The format includes timestamp, log level, and the message
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)
# --- END OF LOGGING SETUP ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This now uses the logger we configured above
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

# --- NEW: LOGGING MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Extract user_id from JWT token if available
    user_id = "anonymous"
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub", "unknown")
        except JWTError:
            user_id = "invalid_token"

    # Process the request
    response = await call_next(request)

    # Calculate processing time
    process_time = (time.time() - start_time) * 1000
    
    # Get client IP address
    ip_address = request.client.host
    
    # Construct the log message
    log_message = (
        f'user="{user_id}" '
        f'ip="{ip_address}" '
        f'method="{request.method}" '
        f'path="{request.url.path}" '
        f'status={response.status_code} '
        f'duration={process_time:.2f}ms'
    )
    
    # Log the message
    logger.info(log_message)
    
    return response
# --- END OF LOGGING MIDDLEWARE ---


# --- CORS MIDDLEWARE CONFIGURATION ---
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
# --- END OF CORS CONFIGURATION ---


app.include_router(auth.router)
app.include_router(config.router)
app.include_router(fortune.router)
app.include_router(users.router)
app.include_router(admin.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the DailyFortune API!"}