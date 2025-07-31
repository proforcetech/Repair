# file backend/app/auth/routes.py
# This file contains user authentication routes for login, logout, password reset, and 2FA setup.
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.dependencies import get_current_user, require_role
from app.core.security import verify_password, create_access_token
from app.db.prisma_client import db
from pydantic import BaseModel
from fastapi import Request
from app.core.notifier import send_email
from datetime import datetime, timedelta
from geolite2 import geolite2
from prisma import Prisma
from typing import Optional
from fastapi.responses import StreamingResponse
from io import BytesIO
import qrcode
import secrets
import pyotp
import qrcode
from collections import Counter
from user_agents import parse
from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user, require_role
from app.core.security import hash_password
from app.db.prisma_client import db
from datetime import datetime, timedelta
from fastapi.responses import StreamingResponse
from io import BytesIO
from prisma import Prisma
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str


# User Authentication Endpoints
# This will handle user login, logout, and 2FA setup
@router.get("/auth/2fa/setup")
async def setup_2fa(user=Depends(get_current_user)):
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="RepairShop")
    
    # save secret
    await db.user.update(where={"id": user.id}, data={"twoFactorSecret": secret})

    # generate QR
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

# This endpoint handles user login with password and 2FA
@router.post("/auth/login")
async def login_user(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    
    await db.connect()
    user = await db.user.find_unique(where={"email": form_data.username})
    
    if user and user.lockedUntil and user.lockedUntil > datetime.utcnow():
        await db.disconnect()
        raise HTTPException(403, detail="Account locked due to multiple failed attempts")

    if not user or not verify_password(form_data.password, user.hashedPwd):
        if user:
            await db.user.update(where={"id": user.id}, data={
                "failedLogins": user.failedLogins + 1,
                "lockedUntil": datetime.utcnow() + timedelta(minutes=15) if user.failedLogins + 1 >= 5 else None
            })
        await db.warrantyaudit.create(data={
            "action": "LOGIN_FAILED",
            "actorId": user.id if user else "unknown",
            "detail": f"{ip} ({user_agent})"
        })
        await db.disconnect()
        raise HTTPException(401, "Invalid credentials")
    user = await db.user.find_unique(where={"email": data.email})
    await db.disconnect()
    if not user or not security.verify_password(data.password, user.hashedPwd):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.isActive:
        raise HTTPException(status_code=403, detail="Account is disabled")
    token = security.create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

    if not user or not verify_password(form_data.password, user.hashedPwd):
        ip = request.client.host
        location = geolite2.lookup(ip).city if geolite2.lookup(ip) else "Unknown"
        await db.warrantyaudit.create(data={
            "action": "LOGIN_FAILED",
            "actorId": "unknown",
            "detail": f"{ip} ({location})"
        })
        raise HTTPException(401, "Invalid credentials")


    ua = parse(user_agent)

    device = f"{ua.os.family} {ua.os.version_string} on {ua.browser.family} {ua.browser.version_string}"

    await db.user.update(where={"id": user.id}, data={"failedLogins": 0, "lockedUntil": None})
    await db.warrantyaudit.create(data={
        "action": "LOGIN",
        "actorId": user.id,
        "detail": f"Login from {ip_address} ({location})",
        "timestamp": datetime.utcnow()
    })

 class PasswordResetRequest(BaseModel):
    email: EmailStr

 class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    await db.disconnect()
    
# Password Reset Endpoints
@router.post("/reset-password/request")
async def request_password_reset(data: PasswordResetRequest):
    await db.connect()
    user = await db.user.find_unique(where={"email": data.email})
    await db.disconnect()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token = security.create_reset_token(data.email)
    return {"reset_token": token, "note": "Use this token in confirm endpoint"}

# This endpoint confirms the password reset using the token
@router.post("/reset-password/confirm")
async def confirm_password_reset(data: PasswordResetConfirm):
    email = security.verify_reset_token(data.token)
    await db.connect()
    await db.user.update(
        where={"email": email},
        data={"hashedPwd": security.hash_password(data.new_password)}
    )
    await db.disconnect()
    return {"message": "Password has been reset successfully"}

# User Management Endpoints
# This will handle user listing, role management, and 2FA verification
@router.get("/")
async def list_users(skip: int = 0, limit: int = 10, role: Optional[str] = None, user = Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    await db.connect()
    where = {"role": role.upper()} if role else {}
    users = await db.user.find_many(where=where, skip=skip, take=limit)
    await db.disconnect()

    return users

# This endpoint logs out the user and records the action in the audit log
@router.post("/auth/logout")
async def logout(user=Depends(get_current_user)):
    await db.warrantyaudit.create(data={
        "action": "LOGOUT",
        "actorId": user.id,
        "timestamp": datetime.utcnow(),
        "detail": "User logged out"
    })
    return {"message": "Logged out"}




class PasswordResetRequest(BaseModel):
    email: EmailStr

# This endpoint requests a password reset by generating a token and sending an email
@router.post("/auth/request-password-reset")
async def request_password_reset(data: PasswordResetRequest):
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)

    await db.connect()
    user = await db.user.find_unique(where={"email": data.email})
    if user:
        await db.user.update(where={"email": data.email}, data={
            "resetToken": token,
            "resetExpiresAt": expires
        })

        await send_email(
            to=user.email,
            subject="Reset your password",
            body=f"Use this link to reset your password:\n\nhttps://yourapp/reset-password?token={token}"
        )
    await db.disconnect()
    return {"message": "If that email exists, a reset link was sent."}

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

# This endpoint confirms the password reset using the token
@router.post("/auth/reset-password")
async def reset_password(data: PasswordResetConfirm):
    await db.connect()
    user = await db.user.find_first(where={
        "resetToken": data.token,
        "resetExpiresAt": {"gt": datetime.utcnow()}
    })

    if not user:
        await db.disconnect()
        raise HTTPException(400, "Invalid or expired token")

    await db.user.update(where={"id": user.id}, data={
        "hashedPwd": hash_password(data.new_password),
        "resetToken": None,
        "resetExpiresAt": None
    })
    await db.disconnect()
    return {"message": "Password has been reset."}

class Login2FA(BaseModel):
    token: str

# This endpoint verifies the 2FA token provided by the user
@router.post("/auth/2fa/verify")
async def verify_2fa(data: Login2FA, user=Depends(get_current_user)):
    totp = pyotp.TOTP(user.twoFactorSecret)
    if not totp.verify(data.token):
        raise HTTPException(401, detail="Invalid 2FA token")
    return {"message": "2FA verified"}

# Admin Statistics Endpoints
# These endpoints provide statistics about user activity, locked accounts, etc.
@router.get("/admin/stats/locked-users")
async def locked_user_count(user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    one_week_ago = datetime.utcnow() - timedelta(days=7)

    await db.connect()
    count = await db.user.count(
        where={
            "lockedUntil": {"gte": one_week_ago}
        }
    )
    await db.disconnect()
    return {"locked_users_past_week": count}

class Disable2FARequest(BaseModel):
    password: str

# This endpoint disables 2FA for the user after verifying their password
@router.post("/me/2fa/disable")
async def disable_2fa(data: Disable2FARequest, user=Depends(get_current_user)):
    await db.connect()
    fresh_user = await db.user.find_unique(where={"id": user.id})
    await db.disconnect()

    if not verify_password(data.password, fresh_user.hashedPwd):
        raise HTTPException(403, detail="Invalid password")

    await db.connect()
    await db.user.update(where={"id": user.id}, data={
        "twoFactorEnabled": False,
        "twoFactorSecret": None
    })
    await db.disconnect()

    await send_email(
        to=user.email,
        subject="2FA Disabled",
        body="You have disabled two-factor authentication. If this wasn't you, contact support immediately."
    )

    return {"message": "2FA disabled"}

# This endpoint retrieves the failed login attempts for a specific user
@router.get("/admin/users/{user_id}/login-failures")
async def get_user_failed_logins(user_id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    logs = await db.warrantyaudit.find_many(
        where={
            "actorId": user_id,
            "action": "LOGIN_FAILED"
        },
        order={"timestamp": "desc"}
    )
    await db.disconnect()

    return [{"timestamp": log.timestamp, "detail": log.detail} for log in logs]

# This endpoint retrieves the current user's information including last login details
@router.get("/me")
async def get_current_user_info(user=Depends(get_current_user)):
    await db.connect()
    last_login = await db.warrantyaudit.find_first(
        where={"actorId": user.id, "action": "LOGIN"},
        order={"timestamp": "desc"}
    )
    await db.disconnect()

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "createdAt": user.createdAt,
        "lastLogin": last_login.timestamp if last_login else None,
        "lastLoginLocation": last_login.detail if last_login else "N/A"
    }

# This endpoint retrieves the frequency of account lock events in the last 30 days
@router.get("/admin/locked-frequency")
async def get_lock_stats(user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    recent = datetime.utcnow() - timedelta(days=30)

    await db.connect()
    logs = await db.warrantyaudit.find_many(
        where={
            "action": "ACCOUNT_LOCKED",
            "timestamp": {"gte": recent}
        }
    )
    await db.disconnect()


    count = Counter(log.actorId for log in logs)
    return dict(count)
