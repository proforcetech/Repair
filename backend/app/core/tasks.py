## File: backend/app/core/tasks.py
# This file contains scheduled tasks for the application, such as checking part fill rates and sending notifications
# It connects to the Prisma database to fetch part requests and calculates fill rates.
async def check_fill_rate_threshold():
    await db.connect()
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    requests = await db.partrequest.find_many(
        where={"status": "APPROVED", "filledAt": {"not": None}, "createdAt": {"gte": week_ago}}
    )
    timely = [r for r in requests if (r.filledAt - r.createdAt).total_seconds() <= 48 * 3600]
    rate = round(len(timely) / len(requests) * 100, 2) if requests else 100

    if rate < 80:
        await notify_user(
            email="manager@repairshop.com",
            subject="?? Low Part Fill Rate Alert",
            body=f"Only {rate}% of part requests were filled in time this week."
        )
    await db.disconnect()
