from datetime import datetime, timedelta


def calculate_late_fee(invoice, daily_rate: float = 2.0) -> float:
    """
    Calculate late fee based on dueDate + graceDays.
    """
    if not invoice.dueDate:
        return 0.0
    today = datetime.utcnow()
    grace = invoice.dueDate + timedelta(days=invoice.graceDays)
    if today <= grace:
        return 0.0
    days_overdue = (today - grace).days
    return round(days_overdue * daily_rate, 2)


job_start_times = {}  # Temporary in-memory tracker


def start_job_timer(job_id: str):
    job_start_times[job_id] = datetime.utcnow()


def stop_job_timer(job_id: str) -> float:
    if job_id not in job_start_times:
        return 0.0
    end = datetime.utcnow()
    start = job_start_times.pop(job_id)
    return round((end - start).total_seconds() / 3600, 2)
