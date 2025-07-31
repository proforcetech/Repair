# backend/app/integrations/routes.py
# This file handles integration routes for external services.
from fastapi import APIRouter, Request
from datetime import datetime

async def auto_suspend_expired_parts():
    now = datetime.utcnow()
    await db.connect()
    await db.part.update_many(
        where={
            "expiryDate": {"lt": now},
            "isAvailable": True
        },
        data={"isAvailable": False}
    )
    await db.disconnect()
