import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="2022",
    database="facial_attendance"
)

cursor = conn.cursor()
cursor.execute("SELECT VERSION();")
cursor.fetchone()
# cursor.close()
# conn.close()
# CREATE
def create_role(name):
    cursor.execute(
        "INSERT IGNORE INTO roles (name) VALUES (%s)",
        (name,)
    )
    conn.commit()
    if cursor.rowcount == 0:
        print(f"{name} already exists. Skipping...")
        return None
    new_id = cursor.lastrowid
    return new_id
create_role("Admin")
create_role("Teacher")
create_role("Student")
create_role("Parent")

def read_role(role_id):
    cursor.execute(
        "SELECT * FROM roles WHERE id = %s",
        (role_id,)
    )
    return cursor.fetchone()
def get_role(role_id):
    return read_role(role_id)
role = get_role(1)
print(role)

def read_all_roles():
    cursor.execute("SELECT * FROM roles")
    return cursor.fetchall()
roles = read_all_roles()
for role in roles:
    print(role)
def update_role_name(role_id, new_name):
    cursor.execute(
        "UPDATE roles SET name = %s WHERE id = %s",
        (new_name, role_id)
    )
    conn.commit()
    return cursor.rowcount
updated = update_role_name(1, "Super Admin")
print(f"Updated Rows: {updated}")
def delete_role(role_id):
    cursor.execute(
        "DELETE FROM roles WHERE id = %s",
        (role_id,)
    )
    conn.commit()
    return cursor.rowcount
deleted = delete_role(4)
print(f"Deleted Rows: {deleted}")

def create_student(name, face_encoding):
    cursor.execute(
        "INSERT IGNORE INTO students (name, face_encoding, registered_on) VALUES (%s, %s, NOW())",
        (name, face_encoding)
        )                                                                                                                                                                       
    conn.commit()
    if cursor.rowcount==0:
        print(f"{name} already exists.Skipping...")
        return None
    new_id = cursor.lastrowid
    return new_id
create_student("Manoj",'"dample"',)
create_student("Priya",'"dample"',)
create_student("Munaa",'"dample"',)
create_student("Salman",'"dample"',)
create_student("SHALINI",'"dample"',)

def read_student(student_id):
    cursor.execute(
        "SELECT * FROM students WHERE id = %s",
        (student_id,)
    )
    return cursor.fetchone()
def get_student(student_id):
    return read_student(student_id)
student=get_student(1)
print(student)
 
 
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

def create_users(username, password_hash):

    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        print(f"{username} already exists. Skipping...")
        return None
 
    cursor.execute(
        "INSERT INTO users (username, password_hash, created_on) VALUES (%s, %s, NOW())",
        (username, password_hash)
    )
    conn.commit()
    new_id = cursor.lastrowid
    return new_id
 
 
def read_users(username):
    cursor.execute(
        "SELECT * FROM users WHERE username = %s",
        (username,)
    )
    return cursor.fetchone()
 
 
def read_all_users():
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()
 
 
def update_users_password(username, new_password_hash):
    cursor.execute(
        "UPDATE users SET password_hash = %s WHERE username = %s",
        (new_password_hash, username)
    )
    conn.commit()
    return cursor.rowcount
 
 
def delete_users(username):
    cursor.execute(
        "DELETE FROM users WHERE username = %s",
        (username,)
    )
    conn.commit()
    return cursor.rowcount
 
 
create_users("admin1", "hashed_password_1")
create_users("admin2", "hashed_password_2")
create_users("shreshtha", "hashed_password_3")
create_users("admin1", "hashed_password_1")

def create_password_reset_token(user_id, token, expires_at):
    cursor.execute(
        "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
        (user_id, token, expires_at)
    )
    conn.commit()
    new_id = cursor.lastrowid
    return new_id
def read_password_reset_token(token_id):
    cursor.execute(
        "SELECT * FROM password_reset_tokens WHERE id = %s",
        (token_id,)
    )
    return cursor.fetchone()
def read_all_password_reset_tokens():
    cursor.execute(
        "SELECT * FROM password_reset_tokens"
    )
    return cursor.fetchall()
def update_token(token_id, new_token):
    cursor.execute(
        "UPDATE password_reset_tokens SET token = %s WHERE id = %s",
        (new_token, token_id)
    )
    conn.commit()
    return cursor.rowcount
def mark_token_as_used(token_id):
    cursor.execute("UPDATE password_reset_tokens SET used = TRUE WHERE id = %s",
        (token_id,)
    )
    conn.commit()
    return cursor.rowcount
def delete_password_reset_token(token_id):
    cursor.execute(
        "DELETE FROM password_reset_tokens WHERE id = %s",
        (token_id,)
    )
    conn.commit()
    return cursor.rowcount

def create_enrollment_batch(
    uploaded_by,
    file_name,
    total_records,
    successful_records
):
    cursor.execute(
        "INSERT INTO enrollment_batches (uploaded_by, file_name, total_records, successful_records) VALUES (%s, %s, %s, %s)",
        (
            uploaded_by,
            file_name,
            total_records,
            successful_records
        )
    )
    conn.commit()

    new_id = cursor.lastrowid
    return new_id

def read_enrollment_batch(batch_id):
    cursor.execute(
        "SELECT * FROM enrollment_batches WHERE id = %s",
        (batch_id,)
    )
    return cursor.fetchone()

def read_all_enrollment_batches():
    cursor.execute(
        "SELECT * FROM enrollment_batches"
    )
    return cursor.fetchall()

def update_batch_file_name(batch_id, new_file_name):
    cursor.execute(
        "UPDATE enrollment_batches SET file_name = %s WHERE id = %s",
        (new_file_name, batch_id)
    )
    conn.commit()
    return cursor.rowcount

def update_batch_records(
    batch_id,
    total_records,
    successful_records
):
    cursor.execute(
        "UPDATE enrollment_batches SET total_records = %s,successful_records = %s WHERE id = %s",
        (
            total_records,
            successful_records,
            batch_id
        )
    )
    conn.commit()
    return cursor.rowcount

def delete_enrollment_batch(batch_id):
    cursor.execute(
        "DELETE FROM enrollment_batches WHERE id = %s",
        (batch_id,)
    )
    conn.commit()
    return cursor.rowcount
 
def create_attendance(student_id, status):
    cursor.execute(
        "SELECT id FROM attendance WHERE student_id = %s AND attendance_date = CURDATE()",
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
    new_id = cursor.lastrowid
    return new_id
 
 
def read_attendance(student_id):
    cursor.execute(
        "SELECT * FROM attendance WHERE student_id = %s",
        (student_id,)
    )
    return cursor.fetchall()
 
 
def read_today_attendance():
    cursor.execute(
        "SELECT * FROM attendance WHERE attendance_date = CURDATE()"
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
 
 
create_attendance(1, "present")
create_attendance(2, "present")
create_attendance(3, "failed")
create_attendance(1, "present")

def create_leave_request(student_id, start_date, end_date, reason):
    cursor.execute(
        "INSERT INTO leave_requests (student_id, start_date, end_date, reason) VALUES (%s, %s, %s, %s)",
        (student_id, start_date, end_date, reason)
    )
    conn.commit()
    return cursor.lastrowid
def read_leave_request(request_id):
    cursor.execute(
        "SELECT * FROM leave_requests WHERE id = %s",
        (request_id,)
    )
    return cursor.fetchone()
def read_all_leave_requests():
    cursor.execute("SELECT * FROM leave_requests")
    return cursor.fetchall()
def update_leave_status(request_id, status, reviewed_by):
    cursor.execute(
        "UPDATE leave_requests SET status = %s, reviewed_by = %s WHERE id = %s",
        (status, reviewed_by, request_id)
    )
    conn.commit()
    return cursor.rowcount
def delete_leave_request(request_id):
    cursor.execute(
        "DELETE FROM leave_requests WHERE id = %s",
        (request_id,)
    )
    conn.commit()
    return cursor.rowcount

def create_holiday(date, description):
    cursor.execute(
        "INSERT INTO holidays (date, description) VALUES (%s, %s)",
        (date, description)
    )
    conn.commit()
    return cursor.lastrowid
def read_holiday(holiday_id):
    cursor.execute(
        "SELECT * FROM holidays WHERE id = %s",
        (holiday_id,)
    )
    return cursor.fetchone()
def read_all_holidays():
    cursor.execute(
        "SELECT * FROM holidays"
    )
    return cursor.fetchall()
def update_holiday(holiday_id, date, description):
    cursor.execute(
        "UPDATE holidays SET date = %s, description = %s WHERE id = %s",
        (date, description, holiday_id)
    )
    conn.commit()
    return cursor.rowcount
def delete_holiday(holiday_id):
    cursor.execute(
        "DELETE FROM holidays WHERE id = %s",
        (holiday_id,)
    )
    conn.commit()
    return cursor.rowcount

def create_notification(student_id, message, channel):
    cursor.execute(
        "INSERT INTO notifications (student_id, message, channel) VALUES (%s, %s, %s)",
        (student_id, message, channel)
    )
    conn.commit()
    return cursor.lastrowid
def read_notification(notification_id):
    cursor.execute(
        "SELECT * FROM notifications WHERE id = %s",
        (notification_id,)
    )
    return cursor.fetchone()
def read_all_notifications():
    cursor.execute(
        "SELECT * FROM notifications"
    )
    return cursor.fetchall()

def update_notification(notification_id, message, channel):
    cursor.execute(
        "UPDATE notifications SET message = %s,channel = %s WHERE id = %s",
        (message, channel, notification_id)
    )
    conn.commit()
    return cursor.rowcount
def delete_notification(notification_id):
    cursor.execute(
        "DELETE FROM notifications WHERE id = %s",
        (notification_id,)
    )
    conn.commit()
    return cursor.rowcount
cursor.close()
cursor.close()
