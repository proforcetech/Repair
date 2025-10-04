## File: backend/app/core/security.py
# This file contains security-related functions such as password hashing, token creation, and verification.
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from datetime import datetime, timedelta
from passlib.context import CryptContext
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", 15))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def create_password_reset_token(email: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": email, "scope": "password_reset", "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password_reset_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        return None
    except JWTError:
        return None

    if payload.get("scope") != "password_reset":
        return None

    return payload.get("sub")
