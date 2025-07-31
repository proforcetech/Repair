from app.common.models import UserCreate, UserUpdate, UserStatusUpdate, EmailStr
from fastapi import APIRouter, Depends, HTTPException, Path
from typing import Optional
from app.auth.dependencies import get_current_user, require_role
from app.core.security import hash_password
from app.db.prisma_client import db

router = APIRouter()

# Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserStatusUpdate(BaseModel):
    is_active: bool

# Routes

@router.post("/register")
async def register(user: UserCreate, creator = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(creator)
    await db.connect()
    existing = await db.user.find_unique(where={"email": user.email})
    if existing:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="Email already registered")

    created = await db.user.create({
        "email": user.email,
        "hashedPwd": hash_password(user.password),
        "role": user.role.upper(),
        "createdById": creator.id
    })
    await db.disconnect()
    return {"message": "User created", "user": created}

@router.get("/")
async def list_users(skip: int = 0, limit: int = 10, role: Optional[str] = None, user = Depends(get_current_user)):
    require_role(["ADMIN"])(user)
    await db.connect()
    where = {"role": role.upper()} if role else {}
    users = await db.user.find_many(where=where, skip=skip, take=limit)
    await db.disconnect()
    return users

@router.get("/{id}")
async def get_user_by_id(id: str, user = Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    target = await db.user.find_unique(where={"id": id})
    await db.disconnect()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return target

@router.put("/{id}/status")
async def update_user_status(id: str, data: UserStatusUpdate, user = Depends(get_current_user)):
    require_role(["ADMIN"])(user)
    await db.connect()
    updated = await db.user.update(
        where={"id": id},
        data={"isActive": data.is_active}
    )
    await db.disconnect()
    return {"message": f"User {'enabled' if data.is_active else 'disabled'}", "user": updated}

@router.get("/me")
async def get_current_user_info(user=Depends(get_current_user), request: Request):
    await db.warrantyaudit.create(data={
        "action": "TOKEN_USED",
        "actorId": user.id,
        "timestamp": datetime.utcnow(),
        "detail": f"Accessed /me from IP {request.client.host}"
    })
    return user


@router.put("/me")
async def update_own_profile(data: UserUpdate, user = Depends(get_current_user)):
    updates = {}
    if data.email:
        updates["email"] = data.email
    if data.password:
        updates["hashedPwd"] = hash_password(data.password)

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields provided")

    await db.connect()
    updated = await db.user.update(where={"id": user.id}, data=updates)
    await db.disconnect()
    return {"message": "Profile updated", "user": updated}

class TechBayAssignment(BaseModel):
    technician_id: str
    bay_id: str

@router.post("/assign-bay")
async def assign_technician_to_bay(data: TechBayAssignment, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    updated = await db.user.update(
        where={"id": data.technician_id},
        data={"assignedBay": data.bay_id}
    )
    await db.disconnect()
    return {"message": "Technician assigned to bay", "technician": updated}
