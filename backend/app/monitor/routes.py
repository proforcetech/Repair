# backend/app/monitor/routes.py
# This file contains monitoring routes for tracking system health and WebSocket connections.
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user, require_role

APIRouter = APIRouter(prefix="/monitor", tags=["monitor"])

@router.get("/monitor/ws-connections")
async def list_ws_connections(user = Depends(get_current_user)):
    require_role(["ADMIN"])(user)
    return {"connected_technicians": list(connected_techs)}
