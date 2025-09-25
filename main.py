# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # <-- IMPORT THIS
from pymongo import IndexModel, ASCENDING
from pymongo.errors import OperationFailure
from contextlib import asynccontextmanager

from app.db import db
from app.routers import auth, config, fortune, users, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup, create database indexes
    print("Application startup: creating database indexes...")
    try:
        # ... (index creation code remains the same)
        await db.users.create_indexes([
            IndexModel([("username", ASCENDING)], unique=True, name="username_unique"),
            IndexModel([("email", ASCENDING)], unique=True, name="email_unique")
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
    # On shutdown
    print("Application shutdown.")


app = FastAPI(
    title="DailyFortune API",
    description="Backend API for the DailyFortune React application.",
    version="1.0.0",
    lifespan=lifespan
)

# --- CORS MIDDLEWARE CONFIGURATION --- #
# This is the part that fixes the error.

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # You can add your production frontend URL here later
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Specifies the allowed origins
    allow_credentials=True,      # Allows cookies/authorization headers
    allow_methods=["*"],         # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],         # Allows all headers
)
# --- END OF CORS CONFIGURATION --- #


app.include_router(auth.router)
app.include_router(config.router)
app.include_router(fortune.router)
app.include_router(users.router)
app.include_router(admin.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the DailyFortune API!"}