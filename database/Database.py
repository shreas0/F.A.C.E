import os
import mysql.connector

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "facial_attendance")
)

cursor = conn.cursor()


# ---------- Students ----------

def create_student(name, face_encoding):
    cursor.execute(
        "INSERT IGNORE INTO students (name, face_encoding, registered_on) VALUES (%s, %s, NOW())",
        (name, face_encoding)
    )
    conn.commit()
    if cursor.rowcount == 0:
        cursor.execute("SELECT id, face_encoding FROM students WHERE name = %s", (name,))
        existing = cursor.fetchone()
        if existing and existing[1] in (None, "[]", "null", []):
            cursor.execute(
                "UPDATE students SET face_encoding = %s WHERE id = %s",
                (face_encoding, existing[0])
            )
            conn.commit()
            print(f"Added face data to the existing student {name}.")
            return existing[0]
        print(f"{name} already exists. Skipping...")
        return None
    return cursor.lastrowid


def get_student(student_id):
    cursor.execute(
        "SELECT * FROM students WHERE id = %s",
        (student_id,)
    )
    student = cursor.fetchone()
    # End the read transaction so this long-running API connection sees
    # registrations committed by the separate registration process.
    conn.commit()
    return student


def read_all_students():
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    # Finish the read transaction so later session checks see recent admin actions.
    conn.commit()
    return students


def update_student_name(student_id, new_name):
    cursor.execute(
        "UPDATE students SET name = %s WHERE id = %s",
        (new_name, student_id)
    )
    conn.commit()
    return cursor.rowcount


def delete_student(student_id):
    cursor.execute(
        "DELETE FROM students WHERE id = %s",
        (student_id,)
    )
    conn.commit()
    return cursor.rowcount


# ---------- Admins ----------

def create_admin(username, password_hash):
    cursor.execute("SELECT id FROM admins WHERE username = %s", (username,))
    if cursor.fetchone():
        print(f"{username} already exists. Skipping...")
        return None

    cursor.execute(
        "INSERT INTO admins (username, password_hash, created_on) VALUES (%s, %s, NOW())",
        (username, password_hash)
    )
    conn.commit()
    return cursor.lastrowid


def read_admin(username):
    cursor.execute(
        "SELECT * FROM admins WHERE username = %s",
        (username,)
    )
    admin = cursor.fetchone()
    conn.commit()
    return admin


def read_all_admins():
    cursor.execute("SELECT * FROM admins")
    return cursor.fetchall()


def update_admin_password(username, new_password_hash):
    cursor.execute(
        "UPDATE admins SET password_hash = %s WHERE username = %s",
        (new_password_hash, username)
    )
    conn.commit()
    return cursor.rowcount


def delete_admin(username):
    cursor.execute(
        "DELETE FROM admins WHERE username = %s",
        (username,)
    )
    conn.commit()
    return cursor.rowcount


# ---------- Attendance ----------
# NOTE: schema has no `attendance_date` column, only `timestamp`.
# Use DATE(timestamp) = CURDATE() instead of a nonexistent column.

def create_attendance(student_id, status):
    cursor.execute(
        "SELECT id, status FROM attendance WHERE student_id = %s AND DATE(timestamp) = CURDATE()",
        (student_id,)
    )
    existing = cursor.fetchone()
    if existing:
        attendance_id, current_status = existing
        if current_status == "present":
            print(f"Student {student_id} is already marked present today. Skipping...")
            return None

        cursor.execute(
            "UPDATE attendance SET status = %s WHERE id = %s",
            (status, attendance_id)
        )
        conn.commit()
        return attendance_id

    cursor.execute(
        "INSERT INTO attendance (student_id, timestamp, status) VALUES (%s, NOW(), %s)",
        (student_id, status)
    )
    conn.commit()
    return cursor.lastrowid


def get_today_attendance_status(student_id):
    cursor.execute(
        "SELECT status FROM attendance WHERE student_id = %s AND DATE(timestamp) = CURDATE()",
        (student_id,)
    )
    row = cursor.fetchone()
    conn.commit()
    return row[0] if row else None


def start_attendance_session():
    """Start a session and create today's default absent rows for all students."""
    try:
        cursor.execute(
            "SELECT id FROM attendance_sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
        )
        active = cursor.fetchone()
        if active:
            return active[0]

        cursor.execute(
            "INSERT INTO attendance_sessions (started_at, ended_at) VALUES (NOW(), NULL)"
        )
        session_id = cursor.lastrowid
        cursor.execute(
            "INSERT IGNORE INTO attendance (student_id, timestamp, status) "
            "SELECT id, NOW(), 'absent' FROM students"
        )
        conn.commit()
        return session_id
    except Exception:
        conn.rollback()
        raise


def end_attendance_session():
    cursor.execute(
        "UPDATE attendance_sessions SET ended_at = NOW() "
        "WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
    )
    conn.commit()
    return cursor.rowcount


def is_attendance_session_active():
    cursor.execute(
        "SELECT id FROM attendance_sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
    )
    return cursor.fetchone() is not None


def read_attendance(student_id):
    cursor.execute(
        "SELECT * FROM attendance WHERE student_id = %s",
        (student_id,)
    )
    return cursor.fetchall()


def read_today_attendance():
    cursor.execute(
        "SELECT * FROM attendance WHERE DATE(timestamp) = CURDATE()"
    )
    return cursor.fetchall()


def update_attendance(attendance_id, new_status):
    cursor.execute(
        "UPDATE attendance SET status = %s WHERE id = %s",
        (new_status, attendance_id)
    )
    conn.commit()
    return cursor.rowcount


def delete_attendance(attendance_id):
    cursor.execute(
        "DELETE FROM attendance WHERE id = %s",
        (attendance_id,)
    )
    conn.commit()
    return cursor.rowcount


def close():
    cursor.close()
    conn.close()


# ---------- Manual test block ----------
# Only runs when you execute `python database.py` directly.
# Importing this file (e.g. from Flask) will NOT re-insert dummy data.
if __name__ == "__main__":
    create_student("Manoj", '"dample"')
    create_student("Priya", '"dample"')
    create_student("Munaa", '"dample"')
    create_student("Salman", '"dample"')
    create_student("SHALINI", '"dample"')

    print(get_student(1))

    create_admin("admin1", "hashed_password_1")
    create_admin("admin2", "hashed_password_2")
    create_admin("shreshtha", "hashed_password_3")

    create_attendance(1, "present")
    create_attendance(2, "present")
    create_attendance(3, "failed")

    close()
