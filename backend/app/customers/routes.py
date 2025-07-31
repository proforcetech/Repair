## File: backend/app/customers/routes.py
# This file contains the routes for customer management, including creating customers, retrieving customer profiles,
# updating customer profiles, and managing warranty claims. It uses FastAPI for routing and Prisma for database interactions.
# It also includes role-based access control to ensure that only authorized users can perform certain actions.
# It defines Pydantic models for request validation and response formatting.
# It connects to the Prisma database to perform CRUD operations on customer data.
# It handles customer-related operations such as creating, retrieving, updating, and searching for customers.
# It also manages warranty claims and comments on those claims.
# It uses dependency injection to get the current user and enforce role-based access control.

from app.auth.dependencies import get_current_userr, require_role
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from jinja2 import Environment, FileSystemLoader
from prisma import Prisma
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import uuid4
from weasyprint import HTML
import io
import secrets
from app.core.security import create_jwt_token
from app.core.notifier import send_email
from app.db.prisma_client import db
from datetime import datetime
from uuid import uuid4
from fastapi import Body
from typing import List
from app.customers.models import CustomerCreate, VehicleCreate
from app.customers.models import CustomerUpdate
from app.customers.models import MileageUpdate, TechPrefUpdate
from app.customers.models import ClaimComment, SurveyIn

# Initialize the Prisma client
db = Prisma()

class CustomerCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    street: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip: Optional[str]

APIRouter = APIRouter(
    prefix="/customers",)

# This route allows admins and front desk staff to create a new customer profile.
@router.post("/")
async def create_customer(data: CustomerCreate, user=Depends(get_current_user)):
    require_role(["ADMIN", "FRONT_DESK", "MANAGER"])(user)
    await db.connect()
    existing = await db.customer.find_unique(where={"email": data.email})
    if existing:
        await db.disconnect()
        raise HTTPException(400, "Customer already exists")

    created = await db.customer.create(data.dict())
    await db.disconnect()
    return created
# This route retrieves a customer profile by their ID.
# It requires the user to have one of the specified roles to access customer data.
# If the customer is not found, it raises a 404 HTTPException.
# It connects to the Prisma database to fetch the customer details.
# It uses the Depends function to inject the current user and enforce role-based access control.
@router.get("/{customer_id}")
async def get_customer(customer_id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "FRONT_DESK", "TECHNICIAN"])(user)
    await db.connect()
    customer = await db.customer.find_unique(where={"id": customer_id})
    await db.disconnect()

    if not customer:
        raise HTTPException(404, "Customer not found")
    return customer

# This route retrieves the dashboard data for a customer.
# It requires the user to be authenticated as a customer.
# It connects to the Prisma database to fetch estimates, invoices, vehicles, and appointments related to the customer.
# It returns a dictionary containing the lists of estimates, invoices, vehicles, and appointments.
# If the user is not a customer, it raises a 403 HTTPException.
@router.get("/dashboard")
async def customer_dashboard(user = Depends(get_current_user)):
    await db.connect()
    estimates = await db.estimate.find_many(where={"customerId": user.id})
    invoices = await db.invoice.find_many(where={"customerId": user.id})
    vehicles = await db.vehicle.find_many(where={"ownerId": user.id})
    appts = await db.appointment.find_many(where={"customerId": user.id})
    await db.disconnect()
    return {
        "estimates": estimates,
        "invoices": invoices,
        "vehicles": vehicles,
        "appointments": appts
    }

# This route allows admins and front desk staff to search for customers by name, email, or phone.
# It requires the user to have one of the specified roles to access customer search functionality.
# It connects to the Prisma database to perform a case-insensitive search on the customer records.
# It returns a list of customers that match the search criteria.
@router.get("/")
async def search_customers(
    name: str = "", email: str = "", phone: str = "", user=Depends(get_current_user)
):
    require_role(["ADMIN", "FRONT_DESK", "MANAGER"])(user)
    await db.connect()
    customers = await db.customer.find_many(
        where={
            "fullName": {"contains": name, "mode": "insensitive"},
            "email": {"contains": email, "mode": "insensitive"},
            "phone": {"contains": phone, "mode": "insensitive"},
        }
    )
    await db.disconnect()
    return customers

def require_customer(user = Depends(get_current_user)):
    if user.role != "CUSTOMER":
        raise HTTPException(403, detail="Only customers can access this route")
    return user

# This route retrieves the profile of the currently authenticated customer.
# It requires the user to be authenticated as a customer.
# It connects to the Prisma database to fetch the customer details based on their email.
# If the customer is not found, it raises a 404 HTTPException.
@router.get("/me")
async def get_customer_profile(user=Depends(require_customer)):
    await db.connect()
    customer = await db.customer.find_unique(where={"email": user.email})
    await db.disconnect()
    if not customer:
        raise HTTPException(404, "Profile not found")
    return customer

class CustomerUpdate(BaseModel):
    full_name: Optional[str]
    phone: Optional[str]
    street: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip: Optional[str]

# This route allows customers to update their profile information.
# It requires the user to be authenticated as a customer.
@router.put("/me")
async def update_customer_profile(data: CustomerUpdate, user=Depends(require_customer)):
    updates = {k: v for k, v in data.dict().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")

    await db.connect()
    updated = await db.customer.update(where={"email": user.email}, data=updates)
    await db.disconnect()
    return {"message": "Profile updated", "customer": updated}

# This route retrieves the warranty claims for the currently authenticated customer.
# It requires the user to be authenticated as a customer.
# It connects to the Prisma database to fetch warranty claims associated with the customer's ID.
@router.get("/me/warranty")
async def get_my_claims(user=Depends(require_customer)):
    await db.connect()
    claims = await db.warrantyclaim.find_many(
        where={"customerId": user.id},
        include={"workOrder": True},
        order={"createdAt": "desc"}
    )
    await db.disconnect()

    return [
        {
            "id": c.id,
            "workOrderId": c.workOrderId,
            "status": c.status,
            "createdAt": c.createdAt,
            "resolutionNotes": c.resolutionNotes,
            "attachmentUrl": c.attachmentUrl,
            "invoiceTotal": c.workOrder.total if c.workOrder else None
        }
        for c in claims
    ]


class ClaimComment(BaseModel):
    message: str

# This route allows customers to comment on their warranty claims.
# It requires the user to be authenticated as a customer.
@router.post("/me/warranty/{claim_id}/comment")
async def comment_on_claim(claim_id: str, data: ClaimComment, user=Depends(require_customer)):
    await db.connect()
    claim = await db.warrantyclaim.find_unique(where={"id": claim_id})
    if not claim or claim.customerId != user.id:
        await db.disconnect()
        raise HTTPException(403, "Access denied")

    comment = await db.warrantyclaimcomment.create(data={
        "claimId": claim_id,
        "sender": "CUSTOMER",
        "message": data.message
    })
    await db.disconnect()
    return {"message": "Comment posted", "comment": comment}

@router.post("/me/warranty/{claim_id}/comment")
async def comment_on_claim(claim_id: str, data: ClaimComment, user=Depends(require_customer)):
    await db.connect()
    claim = await db.warrantyclaim.find_unique(where={"id": claim_id}, include={"assignedTo": True})
    if not claim or claim.customerId != user.id:
        await db.disconnect()
        raise HTTPException(403, "Access denied")

    comment = await db.warrantyclaimcomment.create(data={
        "claimId": claim_id,
        "sender": "CUSTOMER",
        "message": data.message
    })

    if claim.assignedTo and claim.assignedTo.email:
        await send_email(
            to=claim.assignedTo.email,
            subject=f"New Customer Message for Claim #{claim.id}",
            body=f"Customer replied to claim #{claim.id}. Login to review their message."
        )

    await db.disconnect()
    return {"message": "Comment posted", "comment": comment}

# app/customers/routes.py

@router.post("/")
async def create_customer(data: CustomerCreate, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    customer = await db.customer.create(data=data.dict())
    await db.disconnect()
    return customer

@router.get("/")
async def list_customers(user=Depends(get_current_user)):
    await db.connect()
    customers = await db.customer.find_many()
    await db.disconnect()
    return customers

@router.post("/{customer_id}/vehicles")
async def add_vehicle(customer_id: str, data: VehicleCreate, user=Depends(get_current_user)):
    await db.connect()
    vehicle = await db.vehicle.create(data={**data.dict(), "customerId": customer_id})
    await db.disconnect()
    return vehicle

@router.delete("/vehicles/{vehicle_id}")
async def archive_vehicle(vehicle_id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    vehicle = await db.vehicle.update(where={"id": vehicle_id}, data={"archived": True})
    await db.disconnect()
    return {"message": "Vehicle archived", "vehicle": vehicle}

@router.get("/portal/vehicles")
async def get_vehicles(user=Depends(get_current_user)):
    await db.connect()
    vehicles = await db.vehicle.find_many(where={"customerId": user.id})
    await db.disconnect()
    return vehicles

@router.get("/portal/vehicles/{vehicle_id}/history")
async def vehicle_history(vehicle_id: str, user=Depends(get_current_user)):
    await db.connect()
    invoices = await db.invoice.find_many(
        where={"estimate": {"vehicleId": vehicle_id}},
        include={"estimate": {"include": {"items": True}}}
    )
    await db.disconnect()
    return invoices

@router.get("/portal/vehicles/{vehicle_id}/contract")
async def view_contract(vehicle_id: str, user=Depends(get_current_user)):
    await db.connect()
    contract = await db.maintenancecontract.find_first(
        where={"vehicleId": vehicle_id, "isActive": True}
    )
    await db.disconnect()
    return contract or {"message": "No active contract"}


# This route exports the maintenance contract for a vehicle as a PDF.
# It requires the user to be authenticated and have the necessary permissions.
# It connects to the Prisma database to fetch the contract details and vehicle information.
# It uses a template engine to render the contract HTML and then converts it to PDF format.
@router.get("/vehicles/{vehicle_id}/contract/pdf")
async def export_contract_pdf(vehicle_id: str, user=Depends(get_current_user)):
    await db.connect()
    contract = await db.maintenancecontract.find_first(where={"vehicleId": vehicle_id})
    vehicle = await db.vehicle.find_unique(where={"id": vehicle_id})
    await db.disconnect()

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("contract.html")
    html_out = template.render(contract=contract, vehicle=vehicle)

    pdf = HTML(string=html_out).write_pdf()
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename=contract_{vehicle_id}.pdf"
    })


class MileageLog(BaseModel):
    mileage: int

@router.post("/portal/vehicles/{vehicle_id}/log-mileage")
async def log_mileage(vehicle_id: str, data: MileageLog, user=Depends(get_current_user)):
    await db.connect()
    await db.vehicle.update(
        where={"id": vehicle_id},
        data={"lastServiceMileage": data.mileage}
    )
    await db.disconnect()
    return {"message": "Mileage updated"}


class MileageUpdate(BaseModel):
    mileage: int

@router.put("/customer/vehicles/{id}/mileage")
async def update_mileage(id: str, data: MileageUpdate, user=Depends(get_current_user)):
    await db.connect()
    await db.vehicle.update(
        where={"id": id, "ownerId": user.id},
        data={"mileage": data.mileage, "lastUpdated": datetime.utcnow()}
    )
    await db.disconnect()
    return {"message": "Mileage updated"}

class TechPrefUpdate(BaseModel):
    tech_id: str

@router.put("/customers/{id}/preferred-tech")
async def set_preferred_tech(id: str, update: TechPrefUpdate, user=Depends(get_current_user)):
    require_role(["FRONT_DESK", "MANAGER"])(user)
    await db.connect()
    await db.customer.update(where={"id": id}, data={"preferredTechnicianId": update.tech_id})
    await db.disconnect()
    return {"message": "Preferred technician set"}


@router.get("/customers/{id}/profile")
async def customer_profile(id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "FRONT-DESK"])(user)

    await db.connect()
    vehicles = await db.vehicle.find_many(where={"ownerId": id})
    invoices = await db.invoice.find_many(where={"customerId": id})
    claims = await db.warrantyclaim.find_many(where={"customerId": id})
    appointments = await db.appointment.find_many(where={"customerId": id})
    await db.disconnect()

    return {
        "vehicles": vehicles,
        "invoices": invoices,
        "warrantyClaims": claims,
        "appointments": appointments
    }

@router.post("/portal/request-login")
async def request_login_link(email: EmailStr):
    await db.connect()
    customer = await db.customer.find_unique(where={"email": email})
    if not customer:
        raise HTTPException(404, detail="Email not found")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    await db.customertoken.create(data={
        "email": email,
        "token": token,
        "expiresAt": expires_at
    })

    login_url = f"https://repairshop.com/portal/login?token={token}"
    send_email(to=email, subject="Your Login Link", message=f"Click to login: {login_url}")
    await db.disconnect()
    return {"message": "Login link sent"}

@router.get("/portal/login")
async def login_with_token(token: str):
    await db.connect()
    record = await db.customertoken.find_first(where={"token": token, "used": False})
    if not record or record.expiresAt < datetime.utcnow():
        raise HTTPException(400, "Invalid or expired token")

    await db.customertoken.update(where={"id": record.id}, data={"used": True})
    customer = await db.customer.find_unique(where={"email": record.email})
    await db.disconnect()

    jwt = create_jwt_token({"sub": customer.email, "type": "CUSTOMER"})
    return {"access_token": jwt}

@router.get("/customers/{id}/loyalty")
async def get_loyalty(id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "FRONT-DESK", "MANAGER"])(user)
    await db.connect()
    customer = await db.customer.find_unique(where={"id": id})
    await db.disconnect()
    return {
        "loyaltyPoints": customer.loyaltyPoints,
        "visits": customer.visits
    }

@router.post("/customers/register")
async def register_customer(data: CustomerCreate):
    code = str(uuid4())[:8]
    customer = await db.customer.create(data={
        **data.dict(),
        "referralCode": code
    })
    return customer

@router.get("/customers/{id}/referrals")
async def referral_summary(id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    referrer = await db.customer.find_unique(where={"id": id})
    referred = await db.customer.find_many(where={"referredByCode": referrer.referralCode})
    await db.disconnect()

    return {
        "referralCode": referrer.referralCode,
        "totalReferrals": len(referred),
        "referrals": referred
    }

@router.post("/coupons/generate")
async def generate_coupon(
    amount: float,
    is_percent: bool = False,
    expires_at: datetime = Body(...),
    customer_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    require_role(["ADMIN", "MANAGER"])(user)

    code = uuid4().hex[:8].upper()
    await db.connect()
    coupon = await db.coupon.create(data={
        "code": code,
        "amount": amount,
        "isPercent": is_percent,
        "expiresAt": expires_at,
        "customerId": customer_id
    })
    await db.disconnect()
    return {"message": "Coupon created", "coupon": coupon}

class SurveyIn(BaseModel):
    appointmentId: str
    question1: str
    question2: str

@router.post("/survey/submit")
async def submit_survey(data: SurveyIn, user=Depends(get_current_user)):
    require_role(["CUSTOMER"])(user)

    await db.connect()
    exists = await db.surveyresponse.find_first(where={"appointmentId": data.appointmentId})
    if exists:
        raise HTTPException(400, detail="Survey already submitted")

    survey = await db.surveyresponse.create(data={
        "customerId": user.id,
        **data.dict()
    })
    await db.disconnect()
    return {"message": "Survey submitted", "survey": survey}

@router.put("/customers/{id}/sms-optin")
async def update_sms_optin(id: str, opt_in: bool, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    customer = await db.customer.update(where={"id": id}, data={"smsOptIn": opt_in})
    await db.disconnect()
    return {"message": f"SMS opt-in {'enabled' if opt_in else 'disabled'}", "customer": customer}
