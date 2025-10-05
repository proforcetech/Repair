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
from io import StringIO

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
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Uploaded file must be UTF-8 encoded") from exc

    reader = csv.DictReader(StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is missing a header row")

    required_columns = {"date", "amount", "type"}
    missing_columns = required_columns.difference(reader.fieldnames)
    if missing_columns:
        formatted = ", ".join(sorted(missing_columns))
        raise HTTPException(status_code=400, detail=f"Missing required columns: {formatted}")

    staged_rows = []
    for index, row in enumerate(reader, start=2):
        raw_date = (row.get("date") or "").strip()
        if not raw_date:
            raise HTTPException(status_code=400, detail=f"Row {index}: 'date' is required")
        try:
            parsed_date = datetime.fromisoformat(raw_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Row {index}: invalid date '{raw_date}'") from exc

        raw_amount = row.get("amount")
        if raw_amount is None or str(raw_amount).strip() == "":
            raise HTTPException(status_code=400, detail=f"Row {index}: 'amount' is required")
        try:
            amount = float(raw_amount)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"Row {index}: invalid amount '{raw_amount}'") from exc

        txn_type = (row.get("type") or "").strip()
        if not txn_type:
            raise HTTPException(status_code=400, detail=f"Row {index}: 'type' is required")

        staged_rows.append({
            "date": parsed_date,
            "amount": amount,
            "type": txn_type,
            "memo": (row.get("memo") or "").strip(),
        })

    if not staged_rows:
        return {"message": "No bank transactions to import", "count": 0}

    await db.connect()
    try:
        result = await db.banktransaction.create_many(data=staged_rows)
    finally:
        await db.disconnect()

    created_count = getattr(result, "count", len(staged_rows))
    return {"message": "Bank statement imported", "count": created_count}
