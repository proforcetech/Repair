"""WebSocket routes for broadcasting job updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.broadcast import (
    register_job_connection,
    register_technician_connection,
    unregister_job_connection,
    unregister_technician_connection,
)

router = APIRouter(prefix="/ws", tags=["websockets"])


@router.websocket("/jobs")
async def job_updates_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    register_job_connection(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        unregister_job_connection(websocket)


@router.websocket("/jobs/{tech_id}")
async def technician_job_updates_ws(websocket: WebSocket, tech_id: str) -> None:
    await websocket.accept()
    register_technician_connection(tech_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        unregister_technician_connection(tech_id)
