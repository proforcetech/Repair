# backend/app/core/broadcast.py
# This module handles broadcasting messages to WebSocket connections.
# It is used to send real-time updates to connected clients.

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ws.routes import active_connections
from ws.routes import tech_connections
import json

router = APIRouter(prefix="/broadcast", tags=["broadcast"])


async def broadcast_job_update(job_data: dict):
    message = json.dumps(job_data)
    for ws in active_connections:
        await ws.send_text(message)

async def notify_technician(tech_id: str, data: dict):
    if tech_id in tech_connections:
        await tech_connections[tech_id].send_text(json.dumps(data))
