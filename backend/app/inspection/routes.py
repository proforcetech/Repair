# File: backend/app/inspection/routes.py
# This file contains routes for managing inspections, including templates and results.
# It uses FastAPI's dependency injection system to handle authentication and authorization.

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import Any
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from app.core.pdf import generate_pdf  # wherever your PDF helper lives
from app.core.security import decode_token

router = APIRouter(
    prefix="/inspections",
    tags=["inspections"],
)


# ——— DB dependency ———
async def get_db():
    await db.connect()
    try:
        yield db
    finally:
        await db.disconnect()


# ——— Routes ———

@router.get("/templates/{category}", response_model=Any)
async def get_inspection_template(
    category: str,
    user = Depends(get_current_user),
    db=Depends(get_db),
):
    # only techs & managers may fetch templates
    require_role(["TECHNICIAN", "MANAGER"])(user)

    template = await db.inspectiontemplate.find_first(
        where={"category": category},
        include={"items": True},
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.get("/{inspection_id}/pdf", response_model=FileResponse)
async def export_inspection_pdf(
    inspection_id: str,
    user = Depends(get_current_user),
    db=Depends(get_db),
):
    require_role(["TECHNICIAN", "MANAGER"])(user)

    result = await db.inspectionresult.find_unique(
        where={"id": inspection_id}
    )
    if not result:
        raise HTTPException(status_code=404, detail="Inspection not found")

    # generate a one‑off PDF into your exports folder
    filepath = f"exports/inspection_{inspection_id}.pdf"
    generate_pdf("inspection_form.html", {"result": result}, filepath)

    return FileResponse(
        path=filepath,
        media_type="application/pdf",
        filename=f"inspection_{inspection_id}.pdf",
    )
