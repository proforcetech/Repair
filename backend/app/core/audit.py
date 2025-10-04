# backend/app/core/audit.py

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from prisma import Prisma
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from app.core.security import decode_token
from app.db.prisma_client import db

logger = logging.getLogger(__name__)


class AuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, prisma_client: Prisma = db) -> None:
        super().__init__(app)
        self._prisma = prisma_client

    @asynccontextmanager
    async def _prisma_session(self) -> AsyncIterator[Prisma]:
        should_disconnect = False
        if not self._prisma.is_connected():
            await self._prisma.connect()
            should_disconnect = True
        try:
            yield self._prisma
        finally:
            if should_disconnect:
                await self._prisma.disconnect()

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start_time) * 1000

        auth_header: Optional[str] = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return response

        token = auth_header[7:]
        try:
            payload = decode_token(token)
        except Exception:  # pragma: no cover - defensive logging path
            logger.exception("Failed to decode token for audit logging")
            return response

        email = payload.get("sub") if isinstance(payload, dict) else None
        if not email:
            return response

        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        try:
            async with self._prisma_session() as prisma:
                user = await prisma.user.find_unique(where={"email": email})
                if not user:
                    return response
                await prisma.log.create(
                    {
                        "action": f"{request.method} {request.url.path}",
                        "userId": user.id,
                        "latencyMs": latency_ms,
                        "clientIp": client_ip,
                        "userAgent": user_agent,
                    }
                )
        except Exception:  # pragma: no cover - defensive logging path
            logger.exception("Failed to persist audit log entry")

        return response
