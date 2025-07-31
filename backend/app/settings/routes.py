
# File: backend/app/settings/routes.py
# This file contains user settings routes for managing user preferences and security settings.
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from typing import Optional

router = APIRouter(prefix="/settings", tags=["settings"])

class IPTrustRequest(BaseModel):
    ip: str

@router.post("/me/security/trust-ip")
async def trust_ip(data: IPTrustRequest, user=Depends(get_current_user)):
    updated_ips = list(set(user.knownIps + [data.ip]))

    await db.connect()
    await db.user.update(where={"id": user.id}, data={"knownIps": updated_ips})
    await db.disconnect()

    return {"message": f"IP {data.ip} trusted."}

class SettingsUpdate(BaseModel):
    wantsSmsReminders: Optional[bool]
    wantsEmailReminders: Optional[bool]

@router.put("/me/settings")
async def update_user_settings(data: SettingsUpdate, user=Depends(get_current_user)):
    updates = {k: v for k, v in data.dict().items() if v is not None}
    await db.connect()
    updated = await db.user.update(where={"id": user.id}, data=updates)
    await db.disconnect()
    return {"message": "Settings updated", "user": updated}


@router.post("/roles/{role}/permissions")
async def set_permissions(role: str, perms: list[str], user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)
    await db.connect()
    # remove old
    await db.rolepermission.delete_many(where={"role": role.upper()})
    # add new
    for p in perms:
        resource, action = p.split(":")
        await db.rolepermission.create(data={"role": role.upper(), "resource": resource, "action": action})
    await db.disconnect()
    return {"message": "Permissions updated"}

@router.get("/roles/{role}/permissions")
async def get_permissions(role: str, user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)
    await db.connect()
    perms = await db.rolepermission.find_many(where={"role": role.upper()})
    await db.disconnect()
    return [f"{p.resource}:{p.action}" for p in perms]
