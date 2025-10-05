"""Routes for monitoring websocket connections."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user, require_role
from app.core.broadcast import iter_connected_technicians

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/ws-connections")
async def list_ws_connections(user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)
    return {"connected_technicians": list(iter_connected_technicians())}
