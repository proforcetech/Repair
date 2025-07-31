## File: backend/app/accounting/routes.py
# This file contains the routes for managing vendor bills in the accounting module.
from app.auth.dependencies import get_current_user, require_role
from app.db.prisma_client import db
from fastapi import Depends
from fastapi import APIRouter
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import httpx
from fastapi.responses import RedirectResponse


QB_CLIENT_ID = "..."
QB_CLIENT_SECRET = "..."
QB_REDIRECT_URI = "http://localhost:8000/integrations/quickbooks/callback"

router = APIRouter(
    prefix="/accounting",
    tags=["Accounting"],)

@router.get("/integrations/quickbooks/connect")
def connect_quickbooks():
    scope = "com.intuit.quickbooks.accounting"
    auth_url = (
        f"https://appcenter.intuit.com/connect/oauth2?"
        f"client_id={QB_CLIENT_ID}&redirect_uri={QB_REDIRECT_URI}"
        f"&response_type=code&scope={scope}&state=xyz"
    )
    return RedirectResponse(auth_url)


# Vendor Bills Management 
@router.get("/vendor-bills")
async def list_vendor_bills(
    status: Optional[str] = None,  # "paid", "unpaid", "overdue"
    user = Depends(get_current_user)
):
    require_role(["ACCOUNTANT", "ADMIN"])(user)
    await db.connect()

    now = datetime.utcnow()
    filters = {}

    if status == "paid":
        filters["paid"] = True
    elif status == "unpaid":
        filters["paid"] = False
    elif status == "overdue":
        filters = {
            "paid": False,
            "dueDate": {"lt": now}
        }

    bills = await db.vendorbill.find_many(where=filters)
    await db.disconnect()
    return bills


class VendorBillCreate(BaseModel):
    poId: str
    amount: float
    billDate: datetime
    dueDate: datetime
    note: Optional[str] = None

# Handle recording a vendor bill
# This will create a new vendor bill entry in the system
# It will not handle payment processing, that will be a separate route
# This route is for recording the bill details only
# It will require the user to have the ACCOUNTANT or ADMIN role
@router.post("/vendor-bill-add")
async def record_vendor_bill(data: VendorBillCreate, user = Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)
    await db.connect()
    bill = await db.vendorbill.create(data.dict())
    await db.disconnect()
    return {"message": "Vendor bill recorded", "bill": bill}

class JournalLineInput(BaseModel):
    account: str
    debit: float = 0
    credit: float = 0

class JournalEntryInput(BaseModel):
    date: datetime
    description: str
    lines: list[JournalLineInput]

@router.post("/accounting/journals")
async def create_journal_entry(entry: JournalEntryInput, user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    if round(sum(l.debit for l in entry.lines), 2) != round(sum(l.credit for l in entry.lines), 2):
        raise HTTPException(400, detail="Debits and credits must balance")

    await db.connect()
    j = await db.journalentry.create(data={
        "date": entry.date,
        "description": entry.description
    })
    for line in entry.lines:
        await db.journalline.create(data={
            "entryId": j.id,
            **line.dict()
        })
    await db.disconnect()
    return {"message": "Journal entry created", "id": j.id}

@router.get("/accounting/balance-sheet")
async def balance_sheet(user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    lines = await db.journalline.find_many()
    await db.disconnect()

    balances = {}
    for line in lines:
        balances.setdefault(line.account, 0)
        balances[line.account] += line.debit - line.credit

    return balances  # categorize by account prefix in frontend

@router.get("/accounting/cash-flow")
async def cash_flow(user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    lines = await db.journalline.find_many(where={"account": "Cash"})
    await db.disconnect()

    inflow = sum(l.debit for l in lines)
    outflow = sum(l.credit for l in lines)
    return {
        "cashInflow": inflow,
        "cashOutflow": outflow,
        "netCashFlow": inflow - outflow
    }

@router.get("/accounting/trial-balance")
async def trial_balance(user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    lines = await db.journalline.find_many()
    await db.disconnect()

    summary = {}
    for line in lines:
        if line.account not in summary:
            summary[line.account] = {"debit": 0, "credit": 0}
        summary[line.account]["debit"] += line.debit
        summary[line.account]["credit"] += line.credit

    return summary

@router.post("/accounting/journals/{id}/approve")
async def approve_journal(id: str, user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    entry = await db.journalentry.update(
        where={"id": id},
        data={"isApproved": True, "approvedBy": user.email}
    )
    await db.disconnect()

    return {"message": "Journal approved", "entry": entry}

@router.post("/accounting/journals/{id}/lock")
async def lock_journal(id: str, user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    entry = await db.journalentry.update(
        where={"id": id},
        data={"isLocked": True}
    )
    await db.disconnect()
    return {"message": "Journal locked", "entry": entry}

@router.post("/accounting/year-end-close")
async def year_end_close(year: int, user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    retained_earnings_account = "Retained Earnings"

    await db.connect()
    lines = await db.journalline.find_many(
        where={
            "entry": {
                "date": {
                    "gte": datetime(year, 1, 1),
                    "lte": datetime(year, 12, 31)
                }
            }
        }
    )
    totals = {}
    for line in lines:
        if not line.account.startswith("Revenue") and not line.account.startswith("Expense"):
            continue
        totals.setdefault(line.account, 0)
        totals[line.account] += line.credit - line.debit

    entry = await db.journalentry.create(data={
        "date": datetime(year, 12, 31),
        "description": f"Year-end close {year}",
        "isApproved": True,
        "isLocked": True
    })

    for account, balance in totals.items():
        await db.journalline.create(data={
            "entryId": entry.id,
            "account": account,
            "debit": balance if balance < 0 else 0,
            "credit": balance if balance > 0 else 0
        })

    net = sum(totals.values())
    await db.journalline.create(data={
        "entryId": entry.id,
        "account": retained_earnings_account,
        "debit": net if net < 0 else 0,
        "credit": net if net > 0 else 0
    })

    await db.disconnect()
    return {"message": "Year closed", "entryId": entry.id}

@router.get("/accounting/dashboard")
async def accountant_dashboard(user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    unpaid_bills = await db.vendorbill.count(where={"isPaid": False})
    unapproved_journals = await db.journalentry.count(where={"isApproved": False})
    cash_lines = await db.journalline.find_many(where={"account": "Cash"})

    inflow = sum(l.debit for l in cash_lines)
    outflow = sum(l.credit for l in cash_lines)
    await db.disconnect()

    return {
        "unpaidBills": unpaid_bills,
        "unapprovedJournals": unapproved_journals,
        "cashInflow": inflow,
        "cashOutflow": outflow,
        "netCashFlow": inflow - outflow
    }

@router.get("/integrations/quickbooks/callback")
async def quickbooks_callback(code: str, state: str):
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
            auth=(QB_CLIENT_ID, QB_CLIENT_SECRET),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": QB_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_data = res.json()
        # store tokens securely
        return {"access_token": token_data}

class AccountIn(BaseModel):
    name: str
    type: str
    code: str

@router.post("/accounting/chart")
async def add_account(data: AccountIn, user=Depends(get_current_user)):
    require_role(["ADMIN"])(user)

    await db.connect()
    account = await db.chartaccount.create(data=data.dict())
    await db.disconnect()
    return account

@router.get("/accounting/chart")
async def list_accounts(user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    chart = await db.chartaccount.find_many()
    await db.disconnect()
    return chart

import csv
from fastapi import UploadFile, File

@router.post("/payroll/import")
async def import_payroll(file: UploadFile = File(...), user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    content = await file.read()
    decoded = content.decode("utf-8").splitlines()
    reader = csv.DictReader(decoded)

    await db.connect()
    for row in reader:
        job_id = row.get("JobID")
        amount = float(row.get("Amount"))
        await db.journalline.create(data={
            "entryId": row.get("EntryID"),
            "account": "Payroll Expense",
            "debit": amount,
            "credit": 0
        })
        if job_id:
            await db.jobexpense.create(data={
                "jobItemId": job_id,
                "type": "PAYROLL",
                "amount": amount
            })
    await db.disconnect()

    return {"message": "Payroll imported"}

@router.post("/integrations/quickbooks/sync-invoices")
async def sync_invoices_to_qb(user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    invoices = await db.invoice.find_many(where={"syncedToQB": False, "status": "APPROVED"})

    for inv in invoices:
        # construct payload per QuickBooks Invoice schema
        payload = {
            "CustomerRef": {"value": inv.customerId},
            "Line": [{
                "DetailType": "SalesItemLineDetail",
                "Amount": inv.totalAmount,
                "SalesItemLineDetail": {"ItemRef": {"value": "1"}}  # map to item/service ID
            }],
            "TotalAmt": inv.totalAmount
        }

        async with httpx.AsyncClient() as client:
            r = await client.post("https://sandbox-quickbooks.api.intuit.com/v3/company/<realmId>/invoice",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                })

            if r.status_code == 200:
                result = r.json()
                await db.invoice.update(where={"id": inv.id}, data={
                    "syncedToQB": True,
                    "qbInvoiceId": result.get("Invoice", {}).get("Id")
                })

    await db.disconnect()
    return {"message": "Invoices synced"}


total_debit = sum(l.debit for l in entry.lines)
total_credit = sum(l.credit for l in entry.lines)

if round(total_debit, 2) != round(total_credit, 2):
    raise HTTPException(status_code=400, detail="Journal not balanced")

@router.get("/accounting/journals/validate")
async def validate_all_journals(user=Depends(get_current_user)):
    require_role(["ACCOUNTANT", "ADMIN"])(user)

    await db.connect()
    entries = await db.journalentry.find_many(include={"lines": True})
    await db.disconnect()

    unbalanced = []
    for entry in entries:
        debit = sum(l.debit for l in entry.lines)
        credit = sum(l.credit for l in entry.lines)
        if round(debit, 2) != round(credit, 2):
            unbalanced.append({"id": entry.id, "debit": debit, "credit": credit})

    return {"unbalanced": unbalanced}
