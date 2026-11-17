from datetime import date, timedelta

from feature_database import get_connection


def request_leave(student_id, start_date, end_date, reason):
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start or not reason.strip():
        raise ValueError("Enter a reason and a valid date range")
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO leave_requests (student_id, start_date, end_date, reason) VALUES (%s, %s, %s, %s)",
            (student_id, start_date, end_date, reason.strip()),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        connection.close()


def review_leave(request_id, reviewer_user_id, decision, reviewer_note=""):
    if decision not in ("approved", "rejected"):
        raise ValueError("Decision must be approved or rejected")
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE leave_requests SET status = %s, reviewed_by = %s, reviewer_note = %s "
            "WHERE id = %s AND status = 'pending'",
            (decision, reviewer_user_id, reviewer_note.strip(), request_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        cursor.close()
        connection.close()


def get_approved_leave_dates(student_id, start_date, end_date):
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT start_date, end_date FROM leave_requests WHERE student_id = %s "
            "AND status = 'approved' AND start_date <= %s AND end_date >= %s",
            (student_id, end_date, start_date),
        )
        requests = cursor.fetchall()
        days = set()
        for request in requests:
            current = max(start, request["start_date"])
            last = min(end, request["end_date"])
            while current <= last:
                days.add(current.isoformat())
                current += timedelta(days=1)
        return sorted(days)
    finally:
        cursor.close()
        connection.close()
