"""Utilities for broadcasting messages to WebSocket connections."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Tuple

try:  # pragma: no cover - optional dependency for typing
    from starlette.websockets import WebSocket  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - starlette not installed in tests
    WebSocket = Any  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)

_job_connections: set[WebSocket] = set()
_technician_connections: Dict[str, WebSocket] = {}


def register_job_connection(websocket: WebSocket) -> None:
    """Register a job broadcast WebSocket connection."""

    _job_connections.add(websocket)


def unregister_job_connection(websocket: WebSocket) -> None:
    """Remove a job broadcast WebSocket connection if present."""

    _job_connections.discard(websocket)


def register_technician_connection(tech_id: str, websocket: WebSocket) -> None:
    """Register the WebSocket associated with a technician."""

    _technician_connections[tech_id] = websocket


def unregister_technician_connection(tech_id: str) -> None:
    """Unregister the WebSocket associated with a technician."""

    _technician_connections.pop(tech_id, None)


def iter_job_connections() -> Tuple[WebSocket, ...]:
    """Return a snapshot of active job broadcast connections."""

    return tuple(_job_connections)


def iter_connected_technicians() -> Tuple[str, ...]:
    """Return a snapshot of connected technician identifiers."""

    return tuple(_technician_connections.keys())


def _state_is_connected(state: object) -> bool:
    """Return ``True`` if a websocket state represents an active connection."""

    if state is None:
        return True
    name = getattr(state, "name", state)
    return str(name).upper() == "CONNECTED"


def _should_prune(websocket: WebSocket) -> bool:
    """Check whether a websocket is no longer connected."""

    client_state = getattr(websocket, "client_state", None)
    application_state = getattr(websocket, "application_state", None)
    return not (_state_is_connected(client_state) and _state_is_connected(application_state))


async def _safe_send(websocket: WebSocket, payload: str) -> bool:
    """Attempt to send data and return ``True`` if successful."""

    if _should_prune(websocket):
        return False

    try:
        await websocket.send_text(payload)
        return True
    except Exception:  # pragma: no cover - defensive logging
        logger.warning("Failed to send message to websocket; pruning connection.", exc_info=True)
        return False


async def broadcast_job_update(job_data: dict) -> None:
    """Broadcast job data to all connected WebSocket clients."""

    message = json.dumps(job_data)
    stale: list[WebSocket] = []

    for websocket in iter_job_connections():
        if not await _safe_send(websocket, message):
            stale.append(websocket)

    for websocket in stale:
        unregister_job_connection(websocket)


async def notify_technician(tech_id: str, data: dict) -> None:
    """Send a message to a specific technician if connected."""

    websocket = _technician_connections.get(tech_id)
    if websocket is None:
        return

    message = json.dumps(data)
    if not await _safe_send(websocket, message):
        unregister_technician_connection(tech_id)
