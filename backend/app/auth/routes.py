from collections import Counter
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from user_agents import parse

from app.auth.dependencies import get_current_user, require_role
from app.core.notifier import send_email
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    hash_password,
    verify_password,
    verify_password_reset_token,
)
from app.db.prisma_client import db

router = APIRouter(tags=["auth"])


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class Disable2FARequest(BaseModel):
    password: str


class Login2FA(BaseModel):
    token: str


def _client_context(request: Request) -> tuple[str, str, str]:
    client = request.client
    ip = client.host if client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    ua = parse(user_agent)
    device = f"{ua.os.family} {ua.os.version_string} on {ua.browser.family} {ua.browser.version_string}".strip()
    return ip, user_agent, device


@router.get("/2fa/setup")
async def setup_2fa(user=Depends(get_current_user)):
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="RepairShop")

    await db.connect()
    try:
        await db.user.update(where={"id": user.id}, data={"twoFactorSecret": secret, "twoFactorEnabled": True})
    finally:
        await db.disconnect()

    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@router.post("/login")
async def login_user(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    ip, user_agent, device = _client_context(request)
    now = datetime.utcnow()

    await db.connect()
    try:
        user = await db.user.find_unique(where={"email": form_data.username})

        if not user:
            await db.warrantyaudit.create(
                data={
                    "action": "LOGIN_FAILED",
                    "actorId": None,
                    "detail": f"IP={ip}; UA={user_agent}; Outcome=USER_NOT_FOUND",
                }
            )
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if user.lockedUntil and user.lockedUntil > now:
            await db.warrantyaudit.create(
                data={
                    "action": "LOGIN_LOCKED",
                    "actorId": user.id,
                    "detail": f"IP={ip}; UA={user_agent}; Outcome=LOCKED_UNTIL {user.lockedUntil.isoformat()}",
                }
            )
            raise HTTPException(status_code=403, detail="Account locked due to multiple failed attempts")

        if not verify_password(form_data.password, user.hashedPwd):
            failed_attempts = (user.failedLogins or 0) + 1
            lockout_until: Optional[datetime] = None
            if failed_attempts >= 5:
                lockout_until = now + timedelta(minutes=15)

            await db.user.update(
                where={"id": user.id},
                data={"failedLogins": failed_attempts, "lockedUntil": lockout_until},
            )

            await db.warrantyaudit.create(
                data={
                    "action": "LOGIN_FAILED",
                    "actorId": user.id,
                    "detail": f"IP={ip}; UA={user_agent}; Outcome=INVALID_CREDENTIALS",
                }
            )
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not user.isActive:
            await db.warrantyaudit.create(
                data={
                    "action": "LOGIN_FAILED",
                    "actorId": user.id,
                    "detail": f"IP={ip}; UA={user_agent}; Outcome=ACCOUNT_DISABLED",
                }
            )
            raise HTTPException(status_code=403, detail="Account is disabled")

        if user.twoFactorEnabled:
            form = await request.form()
            token = form.get("two_factor_token")
            if not token and getattr(form_data, "scopes", None):
                token = next(iter(form_data.scopes), None)
            totp = pyotp.TOTP(user.twoFactorSecret)
            if not token or not totp.verify(token):
                await db.warrantyaudit.create(
                    data={
                        "action": "LOGIN_FAILED",
                        "actorId": user.id,
                        "detail": f"IP={ip}; UA={user_agent}; Outcome=INVALID_2FA",
                    }
                )
                raise HTTPException(status_code=401, detail="Invalid two-factor authentication code")

        await db.user.update(
            where={"id": user.id},
            data={"failedLogins": 0, "lockedUntil": None},
        )

        await db.warrantyaudit.create(
            data={
                "action": "LOGIN",
                "actorId": user.id,
                "detail": f"IP={ip}; UA={user_agent}; Device={device}; Outcome=SUCCESS",
            }
        )

        token = create_access_token({"sub": user.email, "role": user.role})
        return {"access_token": token, "token_type": "bearer"}
    finally:
        await db.disconnect()


@router.post("/logout")
async def logout(user=Depends(get_current_user)):
    await db.connect()
    try:
        await db.warrantyaudit.create(
            data={
                "action": "LOGOUT",
                "actorId": user.id,
                "timestamp": datetime.utcnow(),
                "detail": "User logged out",
            }
        )
    finally:
        await db.disconnect()
    return {"message": "Logged out"}


@router.post("/request-password-reset")
async def request_password_reset(data: PasswordResetRequest):
    await db.connect()
    try:
        user = await db.user.find_unique(where={"email": data.email})
        if user:
            token = create_password_reset_token(user.email)
            await send_email(
                to=user.email,
                subject="Reset your password",
                body=f"Use this link to reset your password:\n\nhttps://yourapp/reset-password?token={token}",
            )
    finally:
        await db.disconnect()

    return {"message": "If that email exists, a reset link was sent."}


@router.post("/reset-password")
async def reset_password(data: PasswordResetConfirm):
    email = verify_password_reset_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    await db.connect()
    try:
        user = await db.user.find_unique(where={"email": email})
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        await db.user.update(
            where={"id": user.id},
            data={"hashedPwd": hash_password(data.new_password)},
        )
    finally:
        await db.disconnect()

    return {"message": "Password has been reset."}


@router.post("/2fa/verify")
async def verify_2fa(data: Login2FA, user=Depends(get_current_user)):
    totp = pyotp.TOTP(user.twoFactorSecret)
    if not totp.verify(data.token):
        raise HTTPException(status_code=401, detail="Invalid 2FA token")
    return {"message": "2FA verified"}


@router.post("/me/2fa/disable")
async def disable_2fa(data: Disable2FARequest, user=Depends(get_current_user)):
    await db.connect()
    try:
        fresh_user = await db.user.find_unique(where={"id": user.id})
        if not verify_password(data.password, fresh_user.hashedPwd):
            raise HTTPException(status_code=403, detail="Invalid password")

        await db.user.update(
            where={"id": user.id},
            data={"twoFactorEnabled": False, "twoFactorSecret": None},
        )
    finally:
        await db.disconnect()

    await send_email(
        to=user.email,
        subject="2FA Disabled",
        body="You have disabled two-factor authentication. If this wasn't you, contact support immediately.",
    )

    return {"message": "2FA disabled"}


@router.get("/")
async def list_users(skip: int = 0, limit: int = 10, role: Optional[str] = None, user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    await db.connect()
    try:
        where = {"role": role.upper()} if role else {}
        users = await db.user.find_many(where=where, skip=skip, take=limit)
        return users
    finally:
        await db.disconnect()


@router.get("/admin/stats/locked-users")
async def locked_user_count(user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    one_week_ago = datetime.utcnow() - timedelta(days=7)

    await db.connect()
    try:
        count = await db.user.count(
            where={"lockedUntil": {"gte": one_week_ago}},
        )
        return {"locked_users_past_week": count}
    finally:
        await db.disconnect()


@router.get("/admin/users/{user_id}/login-failures")
async def get_user_failed_logins(user_id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    try:
        logs = await db.warrantyaudit.find_many(
            where={"actorId": user_id, "action": "LOGIN_FAILED"},
            order={"timestamp": "desc"},
        )
        return [{"timestamp": log.timestamp, "detail": log.detail} for log in logs]
    finally:
        await db.disconnect()


@router.get("/me")
async def get_current_user_info(user=Depends(get_current_user)):
    await db.connect()
    try:
        last_login = await db.warrantyaudit.find_first(
            where={"actorId": user.id, "action": "LOGIN"},
            order={"timestamp": "desc"},
        )
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "createdAt": user.createdAt,
            "lastLogin": last_login.timestamp if last_login else None,
            "lastLoginLocation": last_login.detail if last_login else "N/A",
        }
    finally:
        await db.disconnect()


@router.get("/admin/locked-frequency")
async def get_lock_stats(user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    recent = datetime.utcnow() - timedelta(days=30)

    await db.connect()
    try:
        logs = await db.warrantyaudit.find_many(
            where={"action": "ACCOUNT_LOCKED", "timestamp": {"gte": recent}},
        )
        return dict(Counter(log.actorId for log in logs))
    finally:
        await db.disconnect()
