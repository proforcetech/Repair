# backend/app/cron/tasks.py
# This file contains scheduled tasks for the application, such as checking part fill rates and sending notifications
async def generate_recurring_bills():
    today = datetime.utcnow().date()
    await db.connect()
    bills = await db.recurringbill.find_many(
        where={"active": True, "nextDue": {"lte": today}}
    )

    for r in bills:
        await db.vendorbill.create(data={
            "vendor": r.vendor,
            "category": r.category,
            "amount": r.amount,
            "date": r.nextDue,
            "notes": "Auto-generated recurring bill"
        })
        await db.recurringbill.update(
            where={"id": r.id},
            data={"nextDue": r.nextDue + timedelta(days=r.intervalDays)}
        )
    await db.disconnect()
