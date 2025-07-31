# File: backend/app/ws/routes.py
# This file contains WebSocket routes for real-time job updates and notifications.

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

APIRouter = APIRouter(prefix="/ws", tags=["websockets"])

active_connections: List[WebSocket] = []

@router.websocket("/ws/jobs")
async def job_updates_ws(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # placeholder to keep connection alive
    except WebSocketDisconnect:
        active_connections.remove(websocket)

tech_connections: dict[str, WebSocket] = {}

@router.websocket("/ws/jobs/{tech_id}")
async def job_updates_ws(websocket: WebSocket, tech_id: str):
    await websocket.accept()
    tech_connections[tech_id] = websocket
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        del tech_connections[tech_id]

connected_techs: set[str] = set()

@router.websocket("/ws/jobs/{tech_id}")
async def job_updates_ws(websocket: WebSocket, tech_id: str):
    await websocket.accept()
    tech_connections[tech_id] = websocket
    connected_techs.add(tech_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        tech_connections.pop(tech_id, None)
        connected_techs.discard(tech_id)
