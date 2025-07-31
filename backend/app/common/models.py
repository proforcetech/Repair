from pydantic import BaseModel, EmailStr
from typing import Optional, List
from enum import Enum


class Role(str, Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    TECHNICIAN = "TECHNICIAN"
    ACCOUNTANT = "ACCOUNTANT"
    FRONT_DESK = "FRONT_DESK"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Role


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class UserStatusUpdate(BaseModel):
    is_active: bool


class PaymentCreate(BaseModel):
    amount: float
    method: str
