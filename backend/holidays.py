from datetime import date

from feature_database import get_connection


def add_holiday(holiday_date, name):
    date.fromisoformat(holiday_date)
    if not name.strip():
        raise ValueError("Holiday name cannot be empty")
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("INSERT INTO holidays (holiday_date, name) VALUES (%s, %s)",
                       (holiday_date, name.strip()))
        connection.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        connection.close()


def get_holidays(start_date, end_date):
    date.fromisoformat(start_date)
    date.fromisoformat(end_date)
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT holiday_date, name FROM holidays WHERE holiday_date BETWEEN %s AND %s ORDER BY holiday_date",
            (start_date, end_date),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
