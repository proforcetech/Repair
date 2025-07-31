## File: backend/app/auth/dependencies.py
# This file contains dependencies for authentication and authorization in the FastAPI application.
# It includes functions to get the current user, check roles, and handle token validation.
# It uses OAuth2PasswordBearer for token handling and JWT for decoding tokens.
# It also includes a utility function to require specific roles for access control.
# It connects to the database to fetch user details and checks if the user is active.
# The dependencies are used in various routes to ensure that only authorized users can access certain endpoints.
# It raises HTTP exceptions for unauthorized access, invalid tokens, or user not found scenarios.
# It is designed to be used with FastAPI's dependency injection system.
# It is a crucial part of the security layer of the application, ensuring that only authenticated and authorized users can perform certain actions.
# It is used across different modules of the application to enforce security policies.
# It is designed to be reusable and modular, allowing for easy integration into different parts of the application.
# It is a key component of the application's security architecture, providing a robust mechanism for user authentication and authorization.
# It is designed to be extensible, allowing for future enhancements such as additional role checks or token validation mechanisms.
# It is a foundational part of the application's security infrastructure, ensuring that user access is controlled and monitored effectively.

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from typing import List
from app.core.security import decode_token
from app.db.prisma_client import db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def require_role(allowed_roles: List[str]):
    def wrapper(user):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Permission denied")
        return user
    return wrapper

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

    await db.connect()
    user = await db.user.find_unique(where={"email": email})
    await db.disconnect()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.isActive:
        raise HTTPException(status_code=403, detail="Account is disabled")

    return user
