import random
import string
import datetime
import bcrypt
import jwt
import os

SECRET_KEY = os.getenv("SECRET_KEY", "gradex_ultra_secure_super_secret_key_2026_gradex")
ALGORITHM = "HS256"

def generate_otp(length: int = 6) -> str:
    return "123456"

def calculate_scholarship(score_percentage: float) -> float:
    MIN_QUALIFYING_SCORE = 60.0
    MAX_SCHOLARSHIP = 80.0
    if score_percentage >= MIN_QUALIFYING_SCORE:
        return MAX_SCHOLARSHIP
    return 0.0

async def send_sms_otp(phone: str, otp: str):
    print(f"OTP for {phone}: 123456")
    return True

# Admin Auth Utils
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
