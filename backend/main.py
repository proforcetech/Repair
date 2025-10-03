## File: backend/main.py
# This file initializes the FastAPI application, sets up middleware, and includes various routers for different functionalities.
# It handles the root endpoint, adds middleware for audit logging and CORS, and includes routers for authentication, user management, and technician management.
# It also starts a background scheduler on application startup.

from fastapi.middleware.cors import CORSMiddleware
from app.auth.routes import router as auth_router
from app.users.routes import router as user_router
from app.core.audit import AuditLogMiddleware
from app.technicians.routes import router as tech_router
from app.core.scheduler import start as start_scheduler
from app.accounting.routes import router as accounting_router
from app.calendar.routes import router as calendar_router
from app.customers.routes import router as customer_router
from app.customers.vehicles import router as customer_vehicle_router
from app.admin.routes import router as admin_router
from app.alerts.routes import router as alert_router
from app.appointments.routes import router as appointment_router
from app.bank.routes import router as bank_router
from app.estimates.routes import router as estimate_router
from app.expenses.routes import router as expense_router
from app.inventory.routes import router as inventory_router
from app.invoice.routes import router as invoice_router
from app.jobs.routes import router as job_router
from app.monitor.routes import router as monitor_router
from app.payment.routes import router as payment_router
from app.purchase.routes import router as purchase_router
from app.repair.routes import router as repairorder_router
from app.reports.routes import router as report_router
from app.reviews.routes import router as review_router
from app.vehicles.routes import router as vehicle_router
from app.vendors.routes import router as vendor_router
from app.warranty.routes import router as warranty_router

from fastapi import APIRouter, Depends
from fastapi import FastAPI

app = FastAPI()

app.add_middleware(AuditLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounting_router, prefix="/accounting", tags=["Accounting"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(alert_router, prefix="/alerts", tags=["Alerts"])
app.include_router(appointment_router, prefix="/appointments", tags=["Appointments"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(bank_router, prefix="/bank", tags=["Bank"])
app.include_router(calendar_router, prefix="/calendar", tags=["Calendar"])
app.include_router(customer_router, prefix="/customers", tags=["Customers"])
app.include_router(customer_vehicle_router, prefix="/customers", tags=["Customer Vehicles"])
app.include_router(estimate_router, prefix="/estimates", tags=["Estimates"])
app.include_router(expense_router, prefix="/expenses", tags=["Expenses"])
app.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
app.include_router(invoice_router, prefix="/invoices", tags=["Invoices"])
app.include_router(job_router, prefix="/jobs", tags=["Jobs"])
app.include_router(monitor_router, prefix="/monitoring", tags=["Monitoring"])
app.include_router(payment_router, prefix="/payments", tags=["Payments"])
app.include_router(purchase_router, prefix="/purchases", tags=["Purchases"])
app.include_router(repairorder_router, prefix="/repair-orders", tags=["Repair Orders"])
app.include_router(report_router, prefix="/reports", tags=["Reports"])
app.include_router(review_router, prefix="/reviews", tags=["Reviews"])
app.include_router(tech_router, prefix="/tech", tags=["technician"])
app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(vehicle_router, prefix="/vehicles", tags=["Vehicles"])
app.include_router(vendor_router, prefix="/vendors", tags=["Vendors"])
app.include_router(warranty_router, prefix="/warranty", tags=["Warranty Claims"])





@app.on_event("startup")
async def on_startup():
    start_scheduler()

@app.get("/")
async def root():
    return {"message": "Welcome to the main application."}

