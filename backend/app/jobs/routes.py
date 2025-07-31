# backend/app/jobs/routes.py
# This file contains job management routes for handling job creation, scheduling, and status updates.

from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from datetime import datetime

APIRouter = APIRouter(prefix="/jobs", tags=["jobs"])

job_start_times = {}

@router.get("/{job_id}/margin")
async def job_margin(job_id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    job = await db.job.find_unique(where={"id": job_id}, include={"invoice": True})
    parts = await db.partusage.find_many(where={"jobId": job_id})
    logs = await db.jobtimelog.find_many(where={"jobId": job_id})

    parts_cost = sum(p.cost * p.quantity for p in parts)
    tech_hours = sum((l.endedAt - l.startedAt).total_seconds() for l in logs if l.endedAt) / 3600
    labor_cost = tech_hours * 25  # example fixed rate or from settings

    invoice_total = job.invoice.total if job.invoice else 0
    total_cost = parts_cost + labor_cost

    margin_pct = round((invoice_total - total_cost) / invoice_total * 100, 2) if invoice_total else 0

    await db.disconnect()
    return {
        "invoice_total": invoice_total,
        "parts_cost": round(parts_cost, 2),
        "labor_cost": round(labor_cost, 2),
        "total_cost": round(total_cost, 2),
        "margin_percent": margin_pct
    }


@router.get("/{job_id}/details")
async def job_detail(job_id: str, user = Depends(get_current_user)):
    await db.connect()

    job = await db.job.find_unique(
        where={"id": job_id},
        include={"technician": True}
    )

    logs = await db.jobtimelog.find_many(where={"jobId": job_id})
    total_time = sum((l.endedAt - l.startedAt).total_seconds() for l in logs if l.endedAt) / 3600

    part_usage = await db.partusage.find_many(where={"jobId": job_id})
    total_parts_cost = sum(p.cost * p.quantity for p in part_usage)

    await db.disconnect()
    return {
        "job": job,
        "technician_hours": round(total_time, 2),
        "parts_cost": round(total_parts_cost, 2),
        "log_entries": len(logs),
        "parts_used": len(part_usage)
    }


@router.put("/{job_id}/status")
async def update_job_status(job_id: str, status: str, user = Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)
    await db.connect()

    updated = await db.job.update(
        where={"id": job_id},
        data={"status": status.upper()}
    )

    # Auto-stop open logs if job is completed
    if status.upper() in ["COMPLETED", "CLOSED"]:
        open_logs = await db.jobtimelog.find_many(
            where={"jobId": job_id, "endedAt": None}
        )
        for log in open_logs:
            await db.jobtimelog.update(
                where={"id": log.id},
                data={"endedAt": datetime.utcnow()}
            )

    await db.disconnect()
    return {"message": "Status updated", "job": updated}



@router.put("/jobs/{job_id}/start")
async def start_job(job_id: str, user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    job_start_times[job_id] = datetime.utcnow()
    await db.connect()
    await db.job.update(where={"id": job_id}, data={"status": "IN_PROGRESS"})
    await db.disconnect()
    return {"message": "Job started"}

@router.put("/jobs/{job_id}/complete")
async def complete_job(job_id: str, user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    end_time = datetime.utcnow()
    start_time = job_start_times.get(job_id)
    duration = round((end_time - start_time).total_seconds() / 3600, 2) if start_time else 0

    await db.connect()
    job = await db.job.update(
        where={"id": job_id},
        data={"status": "COMPLETED", "actualHours": duration}
    )
    await db.disconnect()
    return {"message": "Job completed", "actual_hours": duration}
@router.post("/jobs/{job_id}/apply-template/{template_id}")
async def apply_template_to_job(job_id: str, template_id: str, user = Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)
    await db.connect()

    template = await db.partrequesttemplate.find_unique(
        where={"id": template_id}, include={"items": True}
    )
    if not template:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Template not found")

    for item in template.items:
        await db.jobpart.create({
            "jobId": job_id,
            "sku": item.sku,
            "quantity": item.quantity
        })

    await db.disconnect()
    return {"message": f"Applied template '{template.name}' to job"}

await db.partrequesttemplate.update(
    where={"id": template_id},
    data={"usageCount": {"increment": 1}}
)

@router.get("/request-templates/top-used")
async def get_top_templates(limit: int = 5, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    top = await db.partrequesttemplate.find_many(
        order={"usageCount": "desc"},
        take=limit
    )
    await db.disconnect()
    return top


@router.post("/jobs/{job_id}/generate-invoice")
async def generate_invoice_from_job(job_id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    job = await db.job.find_unique(where={"id": job_id}, include={"parts": True})
    if not job:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Job not found")

    invoice = await db.invoice.create({
        "jobId": job.id,
        "customerId": job.customerId,
        "status": "DRAFT",
        "parts": {
            "create": [
                {
                    "sku": part.sku,
                    "quantity": part.quantity,
                    "unitPrice": part.unitPrice  # or lookup from `part` table
                } for part in job.parts
            ]
        }
    })

    await db.disconnect()
    return {"message": "Invoice created", "invoice": invoice}

class TemplatePartInput(BaseModel):
    sku: str
    quantity: int
    include: bool = True

class ApplyTemplatePayload(BaseModel):
    overrides: list[TemplatePartInput]

@router.post("/jobs/{job_id}/apply-template/{template_id}/custom")
async def apply_template_custom(job_id: str, template_id: str, data: ApplyTemplatePayload, user = Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)
    await db.connect()
    template = await db.partrequesttemplate.find_unique(where={"id": template_id}, include={"items": True})
    if not template:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Template not found")

    for override in data.overrides:
        if override.include:
            await db.jobpart.create({
                "jobId": job_id,
                "sku": override.sku,
                "quantity": override.quantity
            })

    await db.partrequesttemplate.update(
        where={"id": template_id},
        data={"usageCount": {"increment": 1}}
    )

    await db.disconnect()
    return {"message": "Custom template parts added to job"}

@router.get("/template-usage/export")
async def export_template_usage(user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    templates = await db.partrequesttemplate.find_many(order={"usageCount": "desc"})
    await db.disconnect()

    from io import StringIO
    import csv
    from fastapi.responses import StreamingResponse

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Template Name", "Usage Count", "Job Type", "Vehicle Tag"])

    for t in templates:
        writer.writerow([t.name, t.usageCount, t.jobType or "", t.vehicleTag or ""])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=template_usage.csv"
    })
class PartNoteUpdate(BaseModel):
    note: str

@router.put("/job-parts/{part_id}/note")
async def update_job_part_note(part_id: str, data: PartNoteUpdate, user = Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER", "ADMIN"])(user)

    await db.connect()
    updated = await db.jobpart.update(
        where={"id": part_id},
        data={"techNote": data.note}
    )
    await db.disconnect()
    return {"message": "Note updated", "part": updated}

class JobPartCreate(BaseModel):
    sku: str
    quantity: int
    substituted: Optional[bool] = False
    original_sku: Optional[str] = None

@router.post("/jobs/{job_id}/parts")
async def add_part_to_job(job_id: str, data: JobPartCreate, user = Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER"])(user)
    await db.connect()

    part = await db.jobpart.create({
        "jobId": job_id,
        "sku": data.sku,
        "quantity": data.quantity,
        "substituted": data.substituted,
        "originalSku": data.original_sku
    })

    await db.disconnect()
    return {"message": "Part added", "part": part}

from datetime import datetime

await db.jobpart.update_many(
    where={"jobId": invoice.jobId},
    data={"used": True, "usedAt": datetime.utcnow()}
)

from datetime import datetime

@router.post("/jobs")
async def create_job(data: JobCreate, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN", "FRONT-DESK"])(user)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    await db.connect()
    jobs_today = await db.job.find_many(
        where={
            "bayId": data.bay_id,
            "createdAt": {"gte": f"{today}T00:00:00Z", "lte": f"{today}T23:59:59Z"}
        }
    )
    await db.disconnect()

    if len(jobs_today) >= MAX_BAY_JOBS_PER_DAY:
        raise HTTPException(status_code=400, detail="Bay is at capacity for today")

    # Proceed with job creation
    ...
    class ScheduleJob(BaseModel):
    technician_id: str
    bay_id: str
    start: datetime
    end: datetime
    job_type: str
    vehicle_id: str

@router.post("/schedule")
async def schedule_job(data: ScheduleJob, user = Depends(get_current_user)):
    require_role(["MANAGER", "FRONT-DESK"])(user)
    await db.connect()

    overlapping_jobs = await db.job.find_many(
        where={
            "technicianId": data.technician_id,
            "startTime": {"lt": data.end},
            "endTime": {"gt": data.start}
        }
    )

    if overlapping_jobs:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="Technician has overlapping jobs")

    job = await db.job.create({
        "technicianId": data.technician_id,
        "bayId": data.bay_id,
        "startTime": data.start,
        "endTime": data.end,
        "type": data.job_type,
        "vehicleId": data.vehicle_id,
        "status": "SCHEDULED"
    })
    await db.disconnect()
    return job

@router.post("/multi-bay-schedule")
async def schedule_multi_bay_job(data: ScheduleJob, user = Depends(get_current_user)):
    require_role(["MANAGER"])(user)
    await db.connect()

    conflicting = []
    for bay_id in data.bay_ids:
        jobs = await db.job.find_many(
            where={
                "bayIds": {"has": bay_id},
                "startTime": {"lt": data.end},
                "endTime": {"gt": data.start}
            }
        )
        if jobs:
            conflicting.append(bay_id)

    if conflicting:
        await db.disconnect()
        raise HTTPException(status_code=400, detail=f"Bays unavailable: {conflicting}")

    job = await db.job.create({
        "technicianId": data.technician_id,
        "bayIds": data.bay_ids,
        "startTime": data.start,
        "endTime": data.end,
        "vehicleId": data.vehicle_id,
        "type": data.job_type
    })
    await db.disconnect()
    return job

@router.get("/schedule")
async def get_scheduled_jobs(user = Depends(get_current_user)):
    require_role(["MANAGER", "FRONT-DESK"])(user)
    await db.connect()
    jobs = await db.job.find_many()
    await db.disconnect()

    return [
        {
            "id": job.id,
            "title": f"{job.type} - {job.vehicleId}",
            "start": job.startTime,
            "end": job.endTime,
            "type": job.type
        } for job in jobs
    ]

from dateutil.relativedelta import relativedelta

@router.post("/jobs/{id}/recur")
async def create_recurring_instance(id: str, user = Depends(get_current_user)):
    require_role(["MANAGER"])(user)
    await db.connect()
    job = await db.job.find_unique(where={"id": id})

    if not job or not job.isRecurring or not job.recurrence:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="Job is not set to recur")

    delta = relativedelta(months=1) if job.recurrence == "MONTHLY" else relativedelta(weeks=1)

    new_job = await db.job.create({
        "technicianId": job.technicianId,
        "bayIds": job.bayIds,
        "startTime": job.startTime + delta,
        "endTime": job.endTime + delta,
        "type": job.type,
        "vehicleId": job.vehicleId,
        "isRecurring": job.isRecurring,
        "recurrence": job.recurrence
    })
    await db.disconnect()
    return new_job

@router.post("/jobs/{id}/acknowledge")
async def acknowledge_job(id: str, user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    await db.connect()
    job = await db.job.update(
        where={"id": id},
        data={"acknowledged": True, "acknowledgedAt": datetime.utcnow()}
    )
    await db.disconnect()
    return {"message": "Job acknowledged", "job": job}

@router.get("/jobs/unacknowledged")
async def list_unacknowledged_jobs(user = Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    await db.connect()
    jobs = await db.job.find_many(
        where={"technicianId": user.id, "acknowledged": False},
        order={"startTime": "asc"}
    )
    await db.disconnect()
    return jobs

class JobUpdateReason(BaseModel):
    action: str  # "SKIPPED" or "CANCELLED"
    reason: Optional[str] = None

@router.post("/jobs/{id}/status")
async def update_job_status(id: str, data: JobUpdateReason, user = Depends(get_current_user)):
    await db.connect()
    job = await db.job.find_unique(where={"id": id})
    await db.disconnect()

    # Allow managers and admins, or the assigned technician
    if user.role not in ["MANAGER", "ADMIN"] and user.id != job.technicianId:
        raise HTTPException(status_code=403, detail="Not authorized to update this job")

    await db.connect()
    updated = await db.job.update(where={"id": id}, data={"status": data.action})
    await db.jobauditlog.create({
        "jobId": id,
        "action": data.action,
        "reason": data.reason,
        "byUserId": user.id
    })
    await db.disconnect()

    return {"message": f"Job {data.action.lower()} successfully", "job": updated}

@router.get("/jobs/{id}/audit-log")
async def get_job_audit_log(id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN", "TECHNICIAN"])(user)
    await db.connect()
    logs = await db.jobauditlog.find_many(
        where={"jobId": id},
        order={"createdAt": "desc"}
    )
    await db.disconnect()
    return logs

from datetime import datetime, timedelta

@router.post("/jobs/{id}/undo-status")
async def undo_job_status(id: str, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()

    log = await db.jobauditlog.find_first(
        where={"jobId": id},
        order={"createdAt": "desc"}
    )
    job = await db.job.find_unique(where={"id": id})

    if not log or log.action not in ["SKIPPED", "CANCELLED"]:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="No undoable status change found")

    if (datetime.utcnow() - log.createdAt).total_seconds() > 3600:
        await db.disconnect()
        raise HTTPException(status_code=403, detail="Undo window expired")

    restored = await db.job.update(where={"id": id}, data={"status": "SCHEDULED"})
    await db.jobauditlog.create({
        "jobId": id,
        "action": "UNDO_" + log.action,
        "reason": "Undo action",
        "byUserId": user.id
    })
    await db.disconnect()

    return {"message": "Job restored to scheduled", "job": restored}

from app.core.broadcast import broadcast_job_update

# inside update_job_status...
await broadcast_job_update({
    "event": "job_status_updated",
    "jobId": id,
    "status": data.action,
    "updatedBy": user.email
})
await db.jobauditlog.create({
    "jobId": id,
    "action": "UNDO_" + log.action,
    ...
})

if not data.reason:
    raise HTTPException(status_code=400, detail="Reason is required for status updates")

from app.core.broadcast import broadcast_job_update

await broadcast_job_update({
    "event": "job_assigned",
    "jobId": new_job.id,
    "technicianId": new_job.technicianId,
    "startTime": new_job.startTime.isoformat(),
    "type": new_job.type
})

class JobPartAssign(BaseModel):
    jobId: str
    partSku: str
    qty: int

@router.post("/jobs/add-part")
async def assign_part_to_job(data: JobPartAssign, user = Depends(get_current_user)):
    require_role(["MANAGER", "TECHNICIAN"])(user)
    await db.connect()
    part = await db.part.find_unique(where={"sku": data.partSku})
    job = await db.job.find_unique(where={"id": data.jobId})
    if not part or not job:
        await db.disconnect()
        raise HTTPException(status_code=404, detail="Job or Part not found")

    if part.quantity < data.qty:
        await db.disconnect()
        raise HTTPException(status_code=400, detail="Insufficient stock")

    await db.jobpart.create({
        "jobId": data.jobId,
        "partId": part.id,
        "qty": data.qty
    })

    await db.part.update(
        where={"id": part.id},
        data={
            "quantity": part.quantity - data.qty,
            "alert": (part.quantity - data.qty) <= part.minQty
        }
    )
    await db.disconnect()
    return {"message": "Part assigned and stock updated"}

@router.get("/jobs/{job_id}/parts")
async def get_job_parts(job_id: str, user = Depends(get_current_user)):
    await db.connect()
    items = await db.jobpart.find_many(
        where={"jobId": job_id},
        include={"part": True}
    )
    await db.disconnect()
    return [
        {
            "sku": i.part.sku,
            "description": i.part.description,
            "qty": i.qty,
            "cost_per_unit": i.part.cost,
            "total_cost": i.qty * i.part.cost
        } for i in items
    ]


@router.post("/jobs/{job_id}/checklist")
async def attach_checklist(job_id: str, job_type: str):
    await db.connect()
    templates = await db.servicechecklist.find_many(where={"jobType": job_type})
    for item in templates:
        await db.jobchecklistitem.create({
            "jobItemId": job_id,
            "checklistId": item.id
        })
    await db.disconnect()
    return {"added": len(templates)}

@router.put("/jobs/checklist/{item_id}")
async def update_checklist(item_id: str, completed: bool, notes: Optional[str] = None):
    await db.connect()
    await db.jobchecklistitem.update(where={"id": item_id}, data={"completed": completed, "notes": notes})
    await db.disconnect()
    return {"message": "Updated"}

async def create_job_item_with_commission(data: JobItemCreate):
    await db.connect()
    tech = await db.user.find_unique(where={"id": data.technicianId})

    commission = 0
    if tech and tech.isCommissioned and tech.commissionRate:
        commission = round(data.revenue * tech.commissionRate, 2)

    job = await db.jobitem.create(data={**data.dict(), "commission": commission})
    await db.disconnect()
    return job

class JobRating(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    note: Optional[str]

@router.post("/jobs/{job_id}/rate")
async def rate_job(job_id: str, rating: JobRating, user=Depends(get_current_user)):
    await db.connect()
    job = await db.jobitem.find_unique(where={"id": job_id})
    if not job:
        raise HTTPException(404, "Job not found")

    await db.jobitem.update(
        where={"id": job_id},
        data={"customerRating": rating.rating, "ratingNote": rating.note}
    )
    await db.disconnect()
    return {"message": "Thank you for your feedback!"}

class JobStatusUpdate(BaseModel):
    status: str  # Validate "SCHEDULED", "IN_PROGRESS", "COMPLETE"

@router.put("/jobs/{job_id}/status")
async def update_job_status(job_id: str, update: JobStatusUpdate, user=Depends(get_current_user)):
    require_role(["TECHNICIAN", "MANAGER"])(user)

    timestamps = {}
    if update.status == "IN_PROGRESS":
        timestamps["startedAt"] = datetime.utcnow()
    elif update.status == "COMPLETE":
        timestamps["finishedAt"] = datetime.utcnow()

    await db.connect()
    job = await db.jobitem.update(
        where={"id": job_id},
        data={"status": update.status, **timestamps}
    )
    await db.disconnect()
    return {"message": f"Job marked as {update.status}", "job": job}


@router.post("/jobs/{job_id}/notes")
async def add_tech_note(job_id: str, note: str, user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)

    await db.connect()
    await db.jobitem.update(where={"id": job_id}, data={"internalNotes": note})
    await db.disconnect()
    return {"message": "Note saved"}

@router.post("/jobs/{job_id}/attachments")
async def upload_attachment(job_id: str, file: UploadFile = File(...), user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)

    content = await file.read()
    path = f"/attachments/{uuid.uuid4()}-{file.filename}"
    with open(f"static{path}", "wb") as f:
        f.write(content)

    await db.connect()
    await db.jobattachment.create(data={
        "jobItemId": job_id,
        "fileUrl": path,
    })
    await db.disconnect()
    return {"fileUrl": path}

class JobTemplateCreate(BaseModel):
    name: str
    laborOps: list[dict]
    parts: list[dict]
    checklist: list[str]

@router.post("/jobs/templates")
async def create_template(data: JobTemplateCreate, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    template = await db.jobtemplate.create(data=data.dict())
    await db.disconnect()
    return template

@router.post("/jobs/from-template/{template_id}")
async def create_job_from_template(template_id: str, technicianId: str, vehicleId: str, user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    tpl = await db.jobtemplate.find_unique(where={"id": template_id})
    if not tpl:
        raise HTTPException(404, "Template not found")

    job = await db.jobitem.create(data={
        "technicianId": technicianId,
        "vehicleId": vehicleId,
        "hoursBilled": sum(op["hours"] for op in tpl.laborOps),
        "revenue": sum(op["hours"] * op["rate"] for op in tpl.laborOps),
        "status": "SCHEDULED"
    })

    for line in tpl.checklist:
        await db.jobchecklistitem.create({"jobItemId": job.id, "label": line})

    for part in tpl.parts:
        await db.partusage.create({
            "jobItemId": job.id,
            "sku": part["sku"],
            "qty": part["qty"]
        })

    await db.disconnect()
    return job


class JobCommentCreate(BaseModel):
    content: str

@router.post("/jobs/{job_id}/comments")
async def add_job_comment(job_id: str, comment: JobCommentCreate, user=Depends(get_current_user)):
    await db.connect()
    new_comment = await db.jobcomment.create(data={
        "jobItemId": job_id,
        "userId": user.id,
        "content": comment.content
    })
    await db.disconnect()
    return new_comment

@router.get("/jobs/{job_id}/comments")
async def get_job_comments(job_id: str, user=Depends(get_current_user)):
    await db.connect()
    comments = await db.jobcomment.find_many(
        where={"jobItemId": job_id},
        order={"createdAt": "asc"}
    )
    await db.disconnect()
    return comments

@router.post("/jobs/{job_id}/time/start")
async def start_job_timer(job_id: str, user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)
    await db.connect()
    log = await db.jobtimelog.create(data={
        "jobItemId": job_id,
        "technicianId": user.id,
        "startTime": datetime.utcnow()
    })
    await db.disconnect()
    return {"message": "Timer started", "log": log}
@router.post("/jobs/{job_id}/time/stop")
async def stop_job_timer(job_id: str, user=Depends(get_current_user)):
    require_role(["TECHNICIAN"])(user)

    await db.connect()
    log = await db.jobtimelog.find_first(
        where={"jobItemId": job_id, "technicianId": user.id, "endTime": None},
        order={"startTime": "desc"}
    )
    if not log:
        raise HTTPException(404, "No running timer")

    updated = await db.jobtimelog.update(
        where={"id": log.id},
        data={"endTime": datetime.utcnow()}
    )
    await db.disconnect()
    return {"message": "Timer stopped", "log": updated}

class JobTemplateIn(BaseModel):
    name: str
    parts: list[dict]
    labor: list[dict]

@router.post("/jobs/templates")
async def create_template(data: JobTemplateIn, user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    template = await db.jobtemplate.create(data={
        "name": data.name,
        "parts": data.parts,
        "labor": data.labor,
        "createdById": user.id
    })
    await db.disconnect()
    return {"message": "Template saved", "template": template}

class JobTypeIn(BaseModel):
    name: str
    baseHours: float
    basePrice: float

@router.post("/jobs/types")
async def create_job_type(data: JobTypeIn, user=Depends(get_current_user)):
    require_role(["ADMIN", "MANAGER"])(user)
    await db.connect()
    job = await db.jobtype.create(data=data.dict())
    await db.disconnect()
    return job
