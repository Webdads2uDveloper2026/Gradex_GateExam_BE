import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = "gradex_assessment"

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]

# Collections
students_collection = db.get_collection("students")
questions_collection = db.get_collection("questions")
results_collection = db.get_collection("results")
otp_collection = db.get_collection("otps") # For temporary OTP storage
admins_collection = db.get_collection("admins") # For admin users

async def get_db():
    return db
