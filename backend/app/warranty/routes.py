# backend/app/warranty/routes.py
# This file contains warranty claim management routes.

from fastapi import APIRouter, Depends, HTTPException
from fastapi import File, UploadFile
import shutil
import uuid

@router.post("/warranty")
async def submit_warranty_with_attachment(
    data: ClaimCreate = Depends(),
    file: Optional[UploadFile] = File(None),
    user=Depends(require_customer)
):
    await db.connect()

    existing = await db.warrantyclaim.find_first(
        where={"workOrderId": data.work_order_id, "customerId": user.id}
    )
    if existing:
        await db.disconnect()
        raise HTTPException(400, "Claim already submitted")

    attachment_url = None
    if file:
        filename = f"{uuid.uuid4()}_{file.filename}"
        with open(f"attachments/{filename}", "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        attachment_url = f"/attachments/{filename}"

    claim = await db.warrantyclaim.create(data={
        "customerId": user.id,
        "workOrderId": data.work_order_id,
        "description": data.description,
        "attachmentUrl": attachment_url
    })
    await db.disconnect()
    return {"message": "Claim submitted", "claim": claim}


class ClaimStatusUpdate(BaseModel):
    status: str
    resolution_notes: Optional[str]
    
@router.get("/warranty")
async def list_filtered_claims(
    assigned_to_me: Optional[bool] = False,
    unassigned: Optional[bool] = False,
    awaiting_response: Optional[bool] = False,
    user=Depends(get_current_user)
):
    require_role(["ADMIN", "MANAGER", "FRONT_DESK"])(user)

    filters = {}

    if assigned_to_me:
        filters["assignedToId"] = user.id
    elif unassigned:
        filters["assignedToId"] = None

    if awaiting_response:
        filters["status"] = "OPEN"

    await db.connect()
    claims = await db.warrantyclaim.find_many(
        where=filters,
        include={"customer": True, "assignedTo": True},
        order={"createdAt": "desc"}
    )
    await db.disconnect()
    return claims


@router.put("/warranty/{claim_id}/status")
async def update_claim_status(
    claim_id: str,
    data: ClaimStatusUpdate,
    user=Depends(get_current_user)
):
    require_role(["ADMIN", "MANAGER"])(user)

    if data.status not in ["APPROVED", "DENIED"]:
        raise HTTPException(400, "Invalid status")
    
    if data.status == "APPROVED":
    close_date = datetime.utcnow() + timedelta(days=7)  # Auto-close logic placeholder
    # Could be scheduled instead


    await db.connect()
    claim = await db.warrantyclaim.update(
        where={"id": claim_id},
        data={
            "status": data.status,
            "resolutionNotes": data.resolution_notes
        }
    )
    await db.disconnect()

    # Notify customer (if applicable)...

    return {"message": f"Claim {data.status.lower()}", "claim": claim}


@router.post("/warranty/{claim_id}/comment")
async def staff_comment_on_claim(claim_id: str, data: ClaimComment, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "FRONT_DESK"])(user)

    await db.connect()
    claim = await db.warrantyclaim.find_unique(where={"id": claim_id})
    if not claim:
        await db.disconnect()
        raise HTTPException(404, "Claim not found")

    comment = await db.warrantyclaimcomment.create(data={
        "claimId": claim_id,
        "sender": "STAFF",
        "message": data.message
    })
    await db.disconnect()
    return {"message": "Staff comment added", "comment": comment}


@router.get("/warranty/{claim_id}/comments/after")
async def get_new_comments(claim_id: str, since: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "FRONT_DESK", "CUSTOMER"])(user)
    
    since_dt = datetime.fromisoformat(since)

    await db.connect()
    comments = await db.warrantyclaimcomment.find_many(
        where={"claimId": claim_id, "createdAt": {"gt": since_dt}},
        order={"createdAt": "asc"}
    )
    await db.disconnect()
    return comments

@router.get("/warranty/{claim_id}/unread")
async def check_unread_comments(claim_id: str, last_viewed: str, user=Depends(get_current_user)):
    since_dt = datetime.fromisoformat(last_viewed)
    sender_filter = "STAFF" if user.role == "CUSTOMER" else "CUSTOMER"

    await db.connect()
    count = await db.warrantyclaimcomment.count(
        where={
            "claimId": claim_id,
            "createdAt": {"gt": since_dt},
            "sender": sender_filter
        }
    )
    await db.disconnect()
    return {"unread_count": count}

class ClaimAssign(BaseModel):
    user_id: str

@router.put("/warranty/{claim_id}/assign")
async def assign_claim(claim_id: str, data: ClaimAssign, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    claim = await db.warrantyclaim.update(
        where={"id": claim_id},
        data={"assignedToId": data.user_id}
    )
    await db.disconnect()
    return {"message": "Claim assigned", "claim": claim}

@router.post("/warranty/{claim_id}/comment")
async def staff_comment_on_claim(claim_id: str, data: ClaimComment, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "FRONT_DESK"])(user)

    await db.connect()
    claim = await db.warrantyclaim.find_unique(where={"id": claim_id})
    if not claim:
        await db.disconnect()
        raise HTTPException(404, "Claim not found")

    if claim.firstResponseAt is None:
        await db.warrantyclaim.update(where={"id": claim_id}, data={"firstResponseAt": datetime.utcnow()})

    comment = await db.warrantyclaimcomment.create(data={
        "claimId": claim_id,
        "sender": "STAFF",
        "message": data.message
    })

    await db.disconnect()
    return {"message": "Staff comment added", "comment": comment}

@router.get("/warranty/sla/summary")
async def sla_dashboard(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    now = datetime.utcnow()
    SLA_LIMIT_HOURS = 48

    await db.connect()
    claims = await db.warrantyclaim.find_many(
        where={"status": "OPEN"},
        include={"customer": True, "assignedTo": True}
    )
    await db.disconnect()

    breached = []
    upcoming = []

    for c in claims:
        age = (now - c.createdAt).total_seconds() / 3600
        if c.firstResponseAt is None:
            if age > SLA_LIMIT_HOURS:
                breached.append(c)
            elif SLA_LIMIT_HOURS - age <= 6:
                upcoming.append(c)

    return {
        "breached": [c.id for c in breached],
        "upcoming": [c.id for c in upcoming],
        "total_open_claims": len(claims)
    }

@router.get("/warranty/sla/report.csv")
async def export_sla_report(user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    claims = await db.warrantyclaim.find_many()
    await db.disconnect()

    from io import StringIO
    import pandas as pd

    def sla_hours(c):
        if not c.firstResponseAt:
            return None
        return round((c.firstResponseAt - c.createdAt).total_seconds() / 3600, 2)

    rows = [
        {
            "Claim ID": c.id,
            "Customer": c.customerId,
            "Created": c.createdAt,
            "First Response (hrs)": sla_hours(c),
            "Breached": (sla_hours(c) or 999) > 48
        }
        for c in claims
    ]

    df = pd.DataFrame(rows)
    buf = StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sla_report.csv"}
    )

@router.get("/warranty/{claim_id}")
async def get_claim_full_detail(claim_id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER", "FRONT_DESK"])(user)

    await db.connect()
    claim = await db.warrantyclaim.find_unique(
        where={"id": claim_id},
        include={"customer": True, "assignedTo": True}
    )
    comments = await db.warrantyclaimcomment.find_many(
        where={"claimId": claim_id},
        order={"createdAt": "asc"}
    )
    audit = await db.warrantyaudit.find_many(
        where={"claimId": claim_id},
        order={"timestamp": "asc"}
    )
    await db.disconnect()

    return {
        "claim": claim,
        "comments": comments,
        "audit_log": audit
    }

@router.get("/audit")
async def audit_search(
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    claim_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    require_role(["ADMIN", "MANAGER"])(user)

    filters = {}
    if action:
        filters["action"] = action
    if user_id:
        filters["actorId"] = user_id
    if claim_id:
        filters["claimId"] = claim_id

    await db.connect()
    logs = await db.warrantyaudit.find_many(where=filters, order={"timestamp": "desc"})
    await db.disconnect()

    return logs

@router.get("/audit/report.csv")
async def export_audit_csv(month: str, user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    start = datetime.strptime(month, "%Y-%m")
    end = start.replace(day=28) + timedelta(days=4)
    end = end.replace(day=1)

    await db.connect()
    logs = await db.warrantyaudit.find_many(
        where={"timestamp": {"gte": start, "lt": end}},
        include={"claim": True}
    )
    await db.disconnect()

    from io import StringIO
    import pandas as pd

    rows = [
        {
            "Date": log.timestamp,
            "Action": log.action,
            "Actor": log.actorId,
            "Claim ID": log.claimId or "",
            "Detail": log.detail or ""
        } for log in logs
    ]

    df = pd.DataFrame(rows)
    buf = StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"}
    )

@router.put("/warranty/{claim_id}/assign")
async def assign_claim(claim_id: str, data: ClaimAssign, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    claim = await db.warrantyclaim.find_unique(where={"id": claim_id})
    updated = await db.warrantyclaim.update(
        where={"id": claim_id},
        data={"assignedToId": data.user_id}
    )

    await db.warrantyaudit.create(data={
        "claimId": claim_id,
        "action": "CLAIM_ASSIGN",
        "actorId": user.id,
        "detail": f"Reassigned from {claim.assignedToId or 'None'} to {data.user_id}"
    })
    await db.disconnect()

    return {"message": "Claim reassigned", "claim": updated}


@router.post("/warranty-claims/")
async def submit_claim(data: WarrantyClaimCreate, user=Depends(get_current_user)):
    await db.connect()
    claim = await db.warrantyclaim.create(data={
        "workOrderId": data.workOrderId,
        "customerId": user.id,
        "issue": data.issue
    })
    await db.disconnect()
    return {"message": "Claim submitted", "claim": claim}

@router.put("/warranty-claims/{claim_id}/status")
async def update_claim_status(claim_id: str, status: str, notes: Optional[str] = None, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    updated = await db.warrantyclaim.update(
        where={"id": claim_id},
        data={
            "status": status.upper(),
            "notes": notes,
            "resolvedAt": datetime.utcnow()
        }
    )
    await db.disconnect()
    return {"message": "Claim updated", "claim": updated}

@router.get("/warranty-claims/")
async def list_claims(
    status: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    user=Depends(get_current_user)
):
    filters = {}
    if status:
        filters["status"] = status.upper()
    if start and end:
        filters["submittedAt"] = {"gte": start, "lte": end}

    await db.connect()
    claims = await db.warrantyclaim.find_many(where=filters, include={"workOrder": True})
    await db.disconnect()
    return claims

@router.post("/warranty-claims/{claim_id}/upload")
async def upload_claim_attachment(claim_id: str, file: UploadFile = File(...), user=Depends(get_current_user)):
    filename = f"claims/{uuid.uuid4()}_{file.filename}"
    path = f"uploads/{filename}"

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    await db.connect()
    claim = await db.warrantyclaim.update(
        where={"id": claim_id},
        data={"attachments": {"push": path}}
    )
    await db.disconnect()
    return {"message": "Uploaded", "path": path}

@router.get("/warranty/check/{job_id}")
async def check_warranty(job_id: str, user=Depends(get_current_user)):
    await db.connect()
    job = await db.jobitem.find_unique(where={"id": job_id})
    await db.disconnect()
    if not job:
        raise HTTPException(404, "Job not found")

    expired = False
    if job.warrantyMonths:
        expired |= (datetime.utcnow() > job.warrantyStart + relativedelta(months=job.warrantyMonths))
    # Mileage-based checks would need vehicle history / current odo
    return {"warrantyValid": not expired}

@router.get("/warranty/expiring")
async def list_expiring_warranties(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    date_limit = datetime.utcnow() + timedelta(days=30)
    await db.connect()
    jobs = await db.jobitem.find_many(
        where={
            "warrantyStart": {"not": None},
            "warrantyMonths": {"not": None}
        }
    )
    expiring = []
    for job in jobs:
        expiry = job.warrantyStart + relativedelta(months=job.warrantyMonths)
        if expiry <= date_limit:
            expiring.append(job)

    await db.disconnect()
    return expiring

async def notify_contract_expiration():
    await db.connect()
    now = datetime.utcnow()
    expiring = await db.maintenancecontract.find_many(
        where={"endDate": {"lte": now + timedelta(days=7)}}
    )
    
    for contract in expiring:
        customer = await db.customer.find_first(where={"vehicles": {"some": {"id": contract.vehicleId}}})
        if contract.autoRenew:
            # extend contract
            await db.maintenancecontract.update(
                where={"id": contract.id},
                data={"startDate": contract.endDate, "endDate": contract.endDate + relativedelta(months=12)}
            )
        else:
            send_email_or_sms(
                to=customer.email,
                subject="Maintenance Contract Expiring",
                message=f"Your plan '{contract.planName}' expires on {contract.endDate.date()}. Renew now!"
            )
    
    await db.disconnect()

@router.get("/warranty/eligible/{vin}")
async def list_eligible_claims(vin: str, user=Depends(get_current_user)):
    await db.connect()
    
    vehicle = await db.vehicle.find_unique(where={"vin": vin})
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")

    jobs = await db.jobitem.find_many(
        where={
            "vehicleId": vehicle.id,
            "warrantyStart": {"not": None},
            "warrantyMonths": {"not": None}
        }
    )
    
    eligible = []
    for job in jobs:
        expiry = job.warrantyStart + relativedelta(months=job.warrantyMonths)
        if expiry >= datetime.utcnow():
            eligible.append(job)

    await db.disconnect()
    return eligible

class WarrantyIn(BaseModel):
    invoiceId: str
    issue: str

@router.post("/warranty/submit")
async def submit_warranty(data: WarrantyIn, user=Depends(get_current_user)):
    await db.connect()
    invoice = await db.invoice.find_unique(where={"id": data.invoiceId})
    if not invoice or invoice.customerId != user.id:
        raise HTTPException(403, detail="Invalid invoice")

    claim = await db.warrantyclaim.create(data={
        "invoiceId": data.invoiceId,
        "customerId": user.id,
        "issue": data.issue
    })
    await db.disconnect()

    return {"message": "Submitted", "claimId": claim.id}

class WarrantyClaimIn(BaseModel):
    workOrderId: str
    vehicleId: str
    issue: str

@router.post("/warranty/submit")
async def submit_warranty(data: WarrantyClaimIn, user=Depends(get_current_user)):
    require_role(["CUSTOMER", "MANAGER", "ADMIN"])(user)

    await db.connect()
    claim = await db.warrantyclaim.create(data={
        "workOrderId": data.workOrderId,
        "vehicleId": data.vehicleId,
        "issue": data.issue,
        "submittedBy": user.id
    })
    await db.disconnect()
    return {"message": "Warranty claim submitted", "claim": claim}

@router.get("/warranty/{id}/pdf")
async def export_claim_pdf(id: str, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)

    await db.connect()
    claim = await db.warrantyclaim.find_unique(
        where={"id": id},
        include={"vehicle": True, "submittedByUser": True}
    )
    await db.disconnect()

    filepath = f"exports/warranty_{id}.pdf"
    generate_pdf("warranty_claim.html", {"claim": claim}, filepath)

    return FileResponse(filepath, media_type="application/pdf", filename=f"warranty_{id}.pdf")
