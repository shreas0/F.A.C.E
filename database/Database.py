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
        print(f"{name} already exists. Skipping...")
        return None
    return cursor.lastrowid


def get_student(student_id):
    cursor.execute(
        "SELECT * FROM students WHERE id = %s",
        (student_id,)
    )
    return cursor.fetchone()


def read_all_students():
    cursor.execute("SELECT * FROM students")
    return cursor.fetchall()


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
    return cursor.fetchone()


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
        "SELECT id FROM attendance WHERE student_id = %s AND DATE(timestamp) = CURDATE()",
        (student_id,)
    )
    if cursor.fetchone():
        print(f"Student {student_id} already marked today. Skipping...")
        return None

    cursor.execute(
        "INSERT INTO attendance (student_id, timestamp, status) VALUES (%s, NOW(), %s)",
        (student_id, status)
    )
    conn.commit()
    return cursor.lastrowid


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