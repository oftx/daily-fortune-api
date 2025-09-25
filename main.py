# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import IndexModel, ASCENDING
from pymongo.errors import OperationFailure
from contextlib import asynccontextmanager

from app.db import db
from app.routers import auth, config, fortune, users, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup: creating database indexes...")
    try:
        await db.users.create_indexes([
            IndexModel([("username", ASCENDING)], unique=True, name="username_unique"),
            IndexModel([("email", ASCENDING)], unique=True, name="email_unique"),
            # vvv NEW: Add a unique index for the display name vvv
            IndexModel([("display_name", ASCENDING)], unique=True, name="display_name_unique", collation={'locale': 'en', 'strength': 2})
        ])
        await db.fortunes.create_indexes([
            IndexModel([("user_id", ASCENDING)], name="fortune_user_id"),
            IndexModel([("user_id", ASCENDING), ("date", ASCENDING)], unique=True, name="user_date_unique")
        ])
        await db.config.create_indexes([
            IndexModel([("key", ASCENDING)], unique=True, name="config_key_unique")
        ])
        print("Database indexes created successfully.")
    except OperationFailure as e:
        print(f"An error occurred during index creation: {e}")
    yield
    print("Application shutdown.")


app = FastAPI(
    title="DailyFortune API",
    description="Backend API for the DailyFortune React application.",
    version="1.0.0",
    lifespan=lifespan
)

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