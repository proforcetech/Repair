# backend/app/integrations/routes.py
# This file contains routes for integrating with external services like Google Calendar.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from fastapi import Request
from google_auth_oauthlib.flow import Flow

GOOGLE_CLIENT_ID = "your-client-id"
GOOGLE_CLIENT_SECRET = "your-client-secret"

@router.get("/auth/calendar/google/start")
async def google_auth_start():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": ["http://localhost:8000/auth/calendar/google/callback"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar"]
    )
    flow.redirect_uri = "http://localhost:8000/auth/calendar/google/callback"
    auth_url, _ = flow.authorization_url(prompt='consent')
    return {"url": auth_url}

@router.get("/auth/calendar/google/callback")
async def google_auth_callback(request: Request):
    flow = Flow.from_client_config(
        {...}, scopes=["https://www.googleapis.com/auth/calendar"]
    )
    flow.redirect_uri = "http://localhost:8000/auth/calendar/google/callback"
    flow.fetch_token(authorization_response=str(request.url))

    credentials = flow.credentials
    # Save tokens in DB
    ...
    return {"message": "Calendar linked"}


def sync_to_google(user_token, appointment):
    # Load credentials
    creds = Credentials(token=user_token.token, refresh_token=user_token.refresh, ...)
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": f"{appointment.type}",
        "description": appointment.notes,
        "start": {"dateTime": appointment.scheduledAt.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": (appointment.scheduledAt + timedelta(hours=1)).isoformat(), "timeZone": "UTC"},
    }
    service.events().insert(calendarId="primary", body=event).execute()

from twilio.rest import Client

def send_sms(customer_id: str, message: str):
    client = Client(account_sid, auth_token)

    db = Prisma()
    await db.connect()
    customer = await db.customer.find_unique(where={"id": customer_id})
    if customer.smsOptIn:
        try:
            client.messages.create(to=customer.phone, from_="YourNumber", body=message)
            status = "SENT"
        except:
            status = "FAILED"
        await db.smslog.create(data={"customerId": customer.id, "message": message, "status": status})
    await db.disconnect()
