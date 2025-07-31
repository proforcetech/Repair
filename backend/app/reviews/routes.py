# File: backend/app/reviews/routes.py
# This file contains routes for managing technician reviews and customer feedback.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from typing import Optional

router = APIRouter(prefix="/reviews", tags=["reviews"])

class ReviewInput(BaseModel):
    tech_id: str
    note: str

@router.post("/tech-review")
async def add_tech_review(data: ReviewInput, user = Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)
    await db.connect()
    review = await db.userreview.create({
        "techId": data.tech_id,
        "reviewerId": user.id,
        "note": data.note
    })
    await db.disconnect()
    return {"message": "Review submitted", "review": review}


class ReviewIn(BaseModel):
    appointmentId: str
    rating: int
    comments: Optional[str]

@router.post("/reviews")
async def submit_review(data: ReviewIn, user=Depends(get_current_user)):
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(400, detail="Rating must be 1–5")

    await db.connect()
    appt = await db.appointment.find_unique(where={"id": data.appointmentId})
    if not appt or appt.customerId != user.id:
        raise HTTPException(403, detail="Unauthorized")

    review = await db.review.create(data={
        "appointmentId": data.appointmentId,
        "customerId": user.id,
        "rating": data.rating,
        "comments": data.comments,
    })
    await db.disconnect()
    return {"message": "Review submitted", "review": review}

@router.get("/reviews/summary")
async def review_summary(user=Depends(get_current_user)):
    require_role(["MANAGER", "ADMIN"])(user)

    await db.connect()
    reviews = await db.review.find_many()
    avg = sum(r.rating for r in reviews) / len(reviews) if reviews else 0
    await db.disconnect()
    return {"average": round(avg, 2), "total": len(reviews)}

class ReviewIn(BaseModel):
    appointmentId: str
    rating: int
    feedback: Optional[str] = None

@router.post("/reviews")
async def submit_review(data: ReviewIn, user=Depends(get_current_user)):
    require_role(["CUSTOMER"])(user)

    await db.connect()
    existing = await db.review.find_first(where={"appointmentId": data.appointmentId})
    if existing:
        raise HTTPException(400, detail="Review already submitted")

    review = await db.review.create(data={
        "customerId": user.id,
        "appointmentId": data.appointmentId,
        "rating": data.rating,
        "feedback": data.feedback
    })
    await db.disconnect()
    return {"message": "Review submitted", "review": review}
