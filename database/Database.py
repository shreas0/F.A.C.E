"""Small, thread-safe MySQL helpers shared by recognition and API services."""

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
        cursor.execute("SELECT * FROM attendance WHERE DATE(timestamp) = CURDATE() ORDER BY timestamp DESC")
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


def close():
    """Retained for compatibility; connections are opened and closed per call."""
    return None
