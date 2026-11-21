"""Thread-safe MySQL helpers shared by recognition, administrative, and API services."""

from contextlib import contextmanager
import os

import mysql.connector


@contextmanager
def _database_cursor():
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "facial_attendance"),
    )
    cursor = connection.cursor()
    try:
        yield connection, cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


# ── Roles ────────────────────────────────────────────────────────────

def create_role(name):
    with _database_cursor() as (_, cursor):
        cursor.execute("INSERT IGNORE INTO roles (name) VALUES (%s)", (name,))
        if cursor.rowcount == 0:
            return None
        return cursor.lastrowid


def read_role(role_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM roles WHERE id = %s", (role_id,))
        return cursor.fetchone()


def get_role(role_id):
    return read_role(role_id)


def read_all_roles():
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM roles")
        return cursor.fetchall()


def update_role_name(role_id, new_name):
    with _database_cursor() as (_, cursor):
        cursor.execute("UPDATE roles SET name = %s WHERE id = %s", (new_name, role_id))
        return cursor.rowcount


def delete_role(role_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("DELETE FROM roles WHERE id = %s", (role_id,))
        return cursor.rowcount


# ── Students ─────────────────────────────────────────────────────────

def create_student(name, face_encoding):
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "INSERT IGNORE INTO students (name, face_encoding, registered_on) VALUES (%s, %s, NOW())",
            (name, face_encoding),
        )
        if cursor.rowcount:
            return cursor.lastrowid
        cursor.execute("SELECT id, face_encoding FROM students WHERE name = %s", (name,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE students SET face_encoding = %s WHERE id = %s", (face_encoding, existing[0]))
            return existing[0]
        return None


def update_student_face_by_name(name, face_encoding):
    with _database_cursor() as (_, cursor):
        cursor.execute("UPDATE students SET face_encoding = %s WHERE name = %s", (face_encoding, name))
        return cursor.rowcount


def update_student_face_by_id(student_id, face_encoding):
    with _database_cursor() as (_, cursor):
        cursor.execute("UPDATE students SET face_encoding = %s WHERE id = %s", (face_encoding, student_id))
        return cursor.rowcount


def get_student(student_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
        return cursor.fetchone()


def read_student(student_id):
    return get_student(student_id)


def read_all_students():
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT id, name, face_encoding FROM students ORDER BY id")
        return cursor.fetchall()


def update_student_name(student_id, new_name):
    with _database_cursor() as (_, cursor):
        cursor.execute("UPDATE students SET name = %s WHERE id = %s", (new_name, student_id))
        return cursor.rowcount


def delete_student(student_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
        return cursor.rowcount


# ── Users & Admins ───────────────────────────────────────────────────

def create_users(username, password_hash):
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return None
        cursor.execute(
            "INSERT INTO users (username, password_hash, created_on) VALUES (%s, %s, NOW())",
            (username, password_hash),
        )
        return cursor.lastrowid


def read_users(username):
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone()


def read_all_users():
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM users")
        return cursor.fetchall()


def update_users_password(username, new_password_hash):
    with _database_cursor() as (_, cursor):
        cursor.execute("UPDATE users SET password_hash = %s WHERE username = %s", (new_password_hash, username))
        return cursor.rowcount


def delete_users(username):
    with _database_cursor() as (_, cursor):
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        return cursor.rowcount


def create_admin(username, password_hash):
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT id FROM admins WHERE username = %s", (username,))
        if cursor.fetchone():
            return None
        cursor.execute("INSERT INTO admins (username, password_hash) VALUES (%s, %s)", (username, password_hash))
        return cursor.lastrowid


def read_admin(username):
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
        return cursor.fetchone()


def read_all_admins():
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM admins ORDER BY id")
        return cursor.fetchall()


def update_admin_password(username, new_password_hash):
    with _database_cursor() as (_, cursor):
        cursor.execute("UPDATE admins SET password_hash = %s WHERE username = %s", (new_password_hash, username))
        return cursor.rowcount


def delete_admin(username):
    with _database_cursor() as (_, cursor):
        cursor.execute("DELETE FROM admins WHERE username = %s", (username,))
        return cursor.rowcount


# ── Password Reset Tokens ────────────────────────────────────────────

def create_password_reset_token(user_id, token, expires_at):
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
            (user_id, token, expires_at),
        )
        return cursor.lastrowid


def read_password_reset_token(token_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM password_reset_tokens WHERE id = %s", (token_id,))
        return cursor.fetchone()


def read_all_password_reset_tokens():
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM password_reset_tokens")
        return cursor.fetchall()


def update_token(token_id, new_token):
    with _database_cursor() as (_, cursor):
        cursor.execute("UPDATE password_reset_tokens SET token = %s WHERE id = %s", (new_token, token_id))
        return cursor.rowcount


def mark_token_as_used(token_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("UPDATE password_reset_tokens SET used = TRUE WHERE id = %s", (token_id,))
        return cursor.rowcount


def delete_password_reset_token(token_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("DELETE FROM password_reset_tokens WHERE id = %s", (token_id,))
        return cursor.rowcount


# ── Enrollment Batches ───────────────────────────────────────────────

def create_enrollment_batch(uploaded_by, file_name, total_records, successful_records):
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "INSERT INTO enrollment_batches (uploaded_by, file_name, total_records, successful_records) "
            "VALUES (%s, %s, %s, %s)",
            (uploaded_by, file_name, total_records, successful_records),
        )
        return cursor.lastrowid


def read_enrollment_batch(batch_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM enrollment_batches WHERE id = %s", (batch_id,))
        return cursor.fetchone()


def read_all_enrollment_batches():
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM enrollment_batches")
        return cursor.fetchall()


def update_batch_file_name(batch_id, new_file_name):
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "UPDATE enrollment_batches SET file_name = %s WHERE id = %s",
            (new_file_name, batch_id),
        )
        return cursor.rowcount


def update_batch_records(batch_id, total_records, successful_records):
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "UPDATE enrollment_batches SET total_records = %s, successful_records = %s WHERE id = %s",
            (total_records, successful_records, batch_id),
        )
        return cursor.rowcount


def delete_enrollment_batch(batch_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("DELETE FROM enrollment_batches WHERE id = %s", (batch_id,))
        return cursor.rowcount


# ── Attendance ───────────────────────────────────────────────────────

def create_attendance(student_id, status):
    if status not in ("absent", "present", "late", "failed"):
        raise ValueError("Unsupported attendance status")
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "SELECT id, status FROM attendance WHERE student_id = %s AND DATE(timestamp) = CURDATE()",
            (student_id,),
        )
        existing = cursor.fetchone()
        if existing:
            attendance_id, current_status = existing
            if current_status == "present" or status == "absent":
                return None
            cursor.execute("UPDATE attendance SET status = %s WHERE id = %s", (status, attendance_id))
            return attendance_id
        cursor.execute(
            "INSERT INTO attendance (student_id, timestamp, status) VALUES (%s, NOW(), %s)",
            (student_id, status),
        )
        return cursor.lastrowid


def get_today_attendance_status(student_id):
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "SELECT status FROM attendance WHERE student_id = %s AND DATE(timestamp) = CURDATE()",
            (student_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else None


def start_attendance_session():
    """Start a single open session and create default absent rows for today."""
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT id FROM attendance_sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1")
        active = cursor.fetchone()
        if active:
            return active[0]
        cursor.execute("INSERT INTO attendance_sessions (started_at) VALUES (NOW())")
        session_id = cursor.lastrowid
        cursor.execute(
            "INSERT IGNORE INTO attendance (student_id, timestamp, status) "
            "SELECT id, NOW(), 'absent' FROM students"
        )
        return session_id


def end_attendance_session():
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "UPDATE attendance_sessions SET ended_at = NOW() "
            "WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
        )
        return cursor.rowcount


def is_attendance_session_active():
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT id FROM attendance_sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1")
        return cursor.fetchone() is not None


def read_attendance(student_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM attendance WHERE student_id = %s ORDER BY timestamp DESC", (student_id,))
        return cursor.fetchall()


def read_today_attendance():
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "SELECT * FROM attendance WHERE DATE(timestamp) = CURDATE() ORDER BY timestamp DESC"
        )
        return cursor.fetchall()


def update_attendance(attendance_id, new_status):
    if new_status not in ("absent", "present", "late", "failed"):
        raise ValueError("Unsupported attendance status")
    with _database_cursor() as (_, cursor):
        cursor.execute("UPDATE attendance SET status = %s WHERE id = %s", (new_status, attendance_id))
        return cursor.rowcount


def delete_attendance(attendance_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("DELETE FROM attendance WHERE id = %s", (attendance_id,))
        return cursor.rowcount


# ── Leave Requests ───────────────────────────────────────────────────

def create_leave_request(student_id, start_date, end_date, reason):
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "INSERT INTO leave_requests (student_id, start_date, end_date, reason) VALUES (%s, %s, %s, %s)",
            (student_id, start_date, end_date, reason),
        )
        return cursor.lastrowid


def read_leave_request(request_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM leave_requests WHERE id = %s", (request_id,))
        return cursor.fetchone()


def read_all_leave_requests():
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM leave_requests")
        return cursor.fetchall()


def update_leave_status(request_id, status, reviewed_by):
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "UPDATE leave_requests SET status = %s, reviewed_by = %s WHERE id = %s",
            (status, reviewed_by, request_id),
        )
        return cursor.rowcount


def delete_leave_request(request_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("DELETE FROM leave_requests WHERE id = %s", (request_id,))
        return cursor.rowcount


# ── Holidays ─────────────────────────────────────────────────────────

def create_holiday(date, description):
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "INSERT INTO holidays (date, description) VALUES (%s, %s)",
            (date, description),
        )
        return cursor.lastrowid


def read_holiday(holiday_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM holidays WHERE id = %s", (holiday_id,))
        return cursor.fetchone()


def read_all_holidays():
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM holidays")
        return cursor.fetchall()


def update_holiday(holiday_id, date, description):
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "UPDATE holidays SET date = %s, description = %s WHERE id = %s",
            (date, description, holiday_id),
        )
        return cursor.rowcount


def delete_holiday(holiday_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("DELETE FROM holidays WHERE id = %s", (holiday_id,))
        return cursor.rowcount


# ── Notifications ────────────────────────────────────────────────────

def create_notification(student_id, message, channel):
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "INSERT INTO notifications (student_id, message, channel) VALUES (%s, %s, %s)",
            (student_id, message, channel),
        )
        return cursor.lastrowid


def read_notification(notification_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM notifications WHERE id = %s", (notification_id,))
        return cursor.fetchone()


def read_all_notifications():
    with _database_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM notifications")
        return cursor.fetchall()


def update_notification(notification_id, message, channel):
    with _database_cursor() as (_, cursor):
        cursor.execute(
            "UPDATE notifications SET message = %s, channel = %s WHERE id = %s",
            (message, channel, notification_id),
        )
        return cursor.rowcount


def delete_notification(notification_id):
    with _database_cursor() as (_, cursor):
        cursor.execute("DELETE FROM notifications WHERE id = %s", (notification_id,))
        return cursor.rowcount


def close():
    """Retained for compatibility; connections are opened and closed per call."""
    return None
