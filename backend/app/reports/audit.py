# backend/app/reports/audit.py
# This file contains audit report generation and management routes.
from fastapi import APIRouter, Depends
from pydantic import BaseModel  
from datetime import datetime, timedelta
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db

router = APIRouter(prefix="/audit", tags=["audit"])

async def purge_old_audit_logs():
    cutoff = datetime.utcnow() - timedelta(days=365)

    await db.connect()
    deleted = await db.warrantyaudit.delete_many(where={"timestamp": {"lt": cutoff}})
    await db.disconnect()

    return {"deleted_count": deleted.count}


await db.warrantyaudit.create(data={
    "action": "LOGIN",
    "actorId": user.id,
    "timestamp": datetime.utcnow(),
    "detail": "User logged in"
})



<a href="/api/audit/report.csv?month=2025-06" download>
  Download Audit Report
</a>


@router.get("/audit-logs")
async def view_audit_logs(limit: int = 100, user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)
    await db.connect()
    logs = await db.auditlog.find_many(order={"timestamp": "desc"}, take=limit)
    await db.disconnect()
    return logs

@router.get("/audit/vendor-bills")
async def audit_bills(user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    await db.connect()
    bills = await db.vendorbill.find_many(include={"uploadedBy": True})
    await db.disconnect()
    return [
        {
            "id": b.id,
            "vendor": b.vendor,
            "uploadedBy": b.uploadedBy.email,
            "uploadedAt": b.uploadedAt
        } for b in bills
    ]
