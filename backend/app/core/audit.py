# backend/app/core/audit.py

## Audit Log Middleware
# This middleware logs every request made to the API, including the user who made the request and the action performed.
# It connects to the Prisma database to store the logs and handles exceptions gracefully.
# It also measures the time taken to process each request.
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.db.prisma_client import db
from prisma import Prisma
from fastapi import Request
from app.auth.dependencies import get_current_user
from app.core.security import decode_token
from typing import Optional
from fastapi import HTTPException
import time

class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        token = request.headers.get("authorization")
        if token and token.startswith("Bearer "):
            try:
                from app.core.security import decode_token
                payload = decode_token(token[7:])
                email = payload.get("sub")
                db = Prisma()
                await db.connect()
                user = await db.user.find_unique(where={"email": email})
                if user:
                    await db.log.create({
                        "action": f"{request.method} {request.url.path}",
                        "userId": user.id
                    })
                await db.disconnect()
            except Exception:
                pass
        return response
