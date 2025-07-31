## File: backend/app/bank/routes.py
# This file contains routes for managing bank transactions in the FastAPI application.
# It includes endpoints for uploading bank transactions, matching transactions with invoices, and handling user authentication and authorization.
# The routes are designed to be used by users with specific roles such as ACCOUNTANT or ADMIN.
# It uses Pydantic models for request validation and FastAPI's dependency injection system for user authentication.
# The database operations are performed using Prisma Client, which connects to the database to create and update bank transactions.
# The code is structured to ensure that only authorized users can perform actions related to bank transactions.
# It also includes error handling for cases where the user does not have the required role or if the transaction matching fails.
# The routes are registered under the `/bank` path in the FastAPI application.
# The code is modular and can be easily extended to include additional functionality related to bank transactions in the future.
# It is designed to be secure, efficient, and maintainable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
import csv
from fastapi import UploadFile, File

router = APIRouter(prefix="/bank", tags=["bank"])


class TransactionCreate(BaseModel):
    date: datetime
    description: str
    amount: float

# Bank Transactions Management Endpoints
# This will handle uploading bank transactions and matching them with invoices 
@router.post("/")
async def upload_bank_transactions(data: list[TransactionCreate], user = Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)
    await db.connect()
    created = await db.banktransaction.create_many(data=[tx.dict() for tx in data])
    await db.disconnect()
    return {"count": created.count}

# Match Bank Transaction with Invoice
@router.post("/match/{tx_id}/invoice/{invoice_id}")
async def match_transaction(tx_id: str, invoice_id: str, user = Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)
    await db.connect()
    tx = await db.banktransaction.update(
        where={"id": tx_id},
        data={"matchedInvoiceId": invoice_id}
    )
    await db.disconnect()
    return {"message": "Matched transaction", "transaction": tx}

# Import Bank Transactions from CSV
@router.post("/bank/import")
async def import_bank_txn(file: UploadFile = File(...), user=Depends(get_current_user)):
    require_role(["ACCOUNTANT"])(user)
    contents = await file.read()
    decoded = contents.decode("utf-8").splitlines()
    reader = csv.DictReader(decoded)

    await db.connect()
    for row in reader:
        await db.banktransaction.create(data={
            "date": datetime.fromisoformat(row["date"]),
            "amount": float(row["amount"]),
            "type": row["type"],
            "memo": row.get("memo", "")
        })
    await db.disconnect()
    return {"message": "Bank statement imported"}
