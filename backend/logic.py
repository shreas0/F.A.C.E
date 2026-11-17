from datetime import date, timedelta


def get_working_days(start_date, end_date, holidays=(), approved_leave=()):
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise ValueError("end_date must be on or after start_date")

    excluded_dates = {date.fromisoformat(day) for day in holidays}
    excluded_dates.update(date.fromisoformat(day) for day in approved_leave)
    working_days = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in excluded_dates:
            working_days.append(current.isoformat())
        current += timedelta(days=1)
    return working_days


def calculate_attendance_summary(attendance_records, working_days):
    counts = {"present": 0, "absent": 0, "late": 0}
    for record in attendance_records:
        status = record["status"].lower()
        if status in counts:
            counts[status] += 1

    total_days = len(working_days)
    attended_days = counts["present"] + counts["late"]
    percentage = round(attended_days * 100 / total_days, 2) if total_days else 0.0
    return {
        "working_days": total_days,
        "present": counts["present"],
        "late": counts["late"],
        "absent": max(0, total_days - attended_days),
        "attendance_percentage": percentage,
    }


def find_absent_dates(working_days, attendance_records):
    attended_dates = {
        str(record["attendance_date"])
        for record in attendance_records
        if record["status"].lower() in ("present", "late")
    }
    return [day for day in working_days if day not in attended_dates]
