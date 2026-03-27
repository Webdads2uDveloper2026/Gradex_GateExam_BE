import random
import string
import datetime
import bcrypt
import jwt
import os
import httpx

SECRET_KEY = os.getenv("SECRET_KEY", "gradex_ultra_secure_super_secret_key_2026_gradex")
ALGORITHM = "HS256"

def generate_otp(length: int = 4) -> str:
    """Generate a random numeric OTP of specified length."""
    return "".join(random.choices(string.digits, k=length))

def normalize_phone(phone: str) -> str:
    """Consistently normalize phone numbers to digits only with country code."""
    if not phone:
        return ""
    # Remove all non-digit characters
    digits = "".join(filter(str.isdigit, phone))
    # If 10 digits, assume 91 country code
    if len(digits) == 10:
        return f"91{digits}"
    return digits

def calculate_scholarship(score_percentage: float) -> float:
    MIN_QUALIFYING_SCORE = 60.0
    MAX_SCHOLARSHIP = 80.0
    if score_percentage >= MIN_QUALIFYING_SCORE:
        return MAX_SCHOLARSHIP
    return 0.0

async def send_sms_otp(phone: str, otp: str):
    """
    Send OTP via 2Factor API.
    Required Env Vars:
    - TWO_FACTOR_API_KEY
    - TWO_FACTOR_OTP_TEMPLATE_NAME
    - TWO_FACTOR_OTP_VAR1_VALUE (Optional)
    """
    api_key = os.getenv("TWO_FACTOR_API_KEY")
    template_name = os.getenv("TWO_FACTOR_OTP_TEMPLATE_NAME")
    var1_value = os.getenv("TWO_FACTOR_OTP_VAR1_VALUE", "Login")

    if os.getenv("NODE_ENV") == "development":
        print(f"DEVELOPMENT MODE: Skipping 2Factor API. OTP for {phone} is {otp}")
        return True

    if not api_key:
        print("TWO_FACTOR_API_KEY is missing in environment variables")
        return False

    if not template_name:
        print("TWO_FACTOR_OTP_TEMPLATE_NAME is missing in environment variables")
        return False

    # Normalize phone: ensures it has a country code (e.g. 91)
    normalized_mobile = normalize_phone(phone)
    
    url = f"https://2factor.in/API/V1/{api_key}/SMS/{normalized_mobile}/{otp}/{template_name}"
    params = {"var1": var1_value}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response_data = response.json()
            
            if response_data.get("Status") == "Success":
                print(f"OTP sent successfully to {normalized_mobile}")
                return True
            else:
                print(f"Failed to send OTP: {response_data.get('Details', 'Unknown Error')}")
                return False
    except Exception as e:
        print(f"Exception while sending OTP: {str(e)}")
        return False

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
