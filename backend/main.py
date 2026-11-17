import os
import re
import sys
from functools import wraps

from flask import Flask, jsonify, request, session
from flask_cors import CORS

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database import Database
from passwords import verify_password
from feature_database import get_connection
from logic import calculate_attendance_summary, find_absent_dates, get_working_days
from holidays import add_holiday, get_holidays
from leaves import get_approved_leave_dates, request_leave, review_leave
from notifications import get_notifications, mark_notification_read, send_notification
from enrollment import import_students_csv
from roles import check_login, create_user
from password_reset import create_reset_token, reset_password


app = Flask(__name__)
app.secret_key = os.getenv("FACE_SESSION_SECRET") or os.urandom(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
CORS(app, supports_credentials=True, origins=["http://localhost:3000", "http://127.0.0.1:3000"])


def login_required(function):
    @wraps(function)
    def check_login_state(*args, **kwargs):
        if not session.get("role"):
            return jsonify({"message": "Please sign in first."}), 401
        return function(*args, **kwargs)
    return check_login_state


def role_required(*allowed_roles):
    def make_check(function):
        @wraps(function)
        def check_role(*args, **kwargs):
            if not session.get("role"):
                return jsonify({"message": "Please sign in first."}), 401
            if session.get("role") not in allowed_roles:
                return jsonify({"message": "You do not have permission for this action."}), 403
            return function(*args, **kwargs)
        return check_role
    return make_check


def get_student(student_id):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id, name FROM students WHERE id = %s", (student_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def get_attendance_rows(start_date, end_date, student_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = (
            "SELECT attendance.id, attendance.student_id, students.name, "
            "attendance.attendance_date, attendance.timestamp, attendance.status "
            "FROM attendance JOIN students ON students.id = attendance.student_id "
            "WHERE attendance.attendance_date BETWEEN %s AND %s"
        )
        values = [start_date, end_date]
        if student_id:
            query += " AND attendance.student_id = %s"
            values.append(student_id)
        query += " ORDER BY attendance.attendance_date DESC, students.name"
        cursor.execute(query, tuple(values))
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


@app.get("/health")
def health():
    return jsonify({"service": "face_api", "status": "ok"})


@app.post("/api/admin/login")
def admin_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = data.get("password", "")
    if not username or not isinstance(password, str) or not password:
        return jsonify({"message": "Enter your admin ID and password."}), 400

    try:
        user = check_login(username, password)
        if user and user["role"] in ("admin", "reviewer"):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return jsonify({"message": "Sign-in successful.", "admin": {
                "id": user["id"], "username": user["username"], "role": user["role"]
            }})
    except Exception:
        app.logger.info("Role login is unavailable; trying the existing admin table.")

    try:
        admin = Database.read_admin(username)
    except Exception:
        app.logger.exception("Could not connect to MySQL")
        return jsonify({"message": "The login API is running, but MySQL is unavailable."}), 503
    if not admin or not verify_password(password, admin[2]):
        return jsonify({"message": "Admin ID or password is incorrect."}), 401

    session.clear()
    session["username"] = admin[1]
    session["role"] = "admin"
    return jsonify({"message": "Sign-in successful.", "admin": {
        "id": admin[0], "username": admin[1], "role": "admin"
    }})


@app.post("/api/student/login")
def student_login():
    data = request.get_json(silent=True) or {}
    student_id = str(data.get("student_id", "")).strip()
    if not student_id.isdigit():
        return jsonify({"message": "Enter a valid student enrollment ID."}), 400
    try:
        student = get_student(int(student_id))
    except Exception:
        app.logger.exception("Could not connect to MySQL")
        return jsonify({"message": "MySQL is unavailable."}), 503
    if not student:
        return jsonify({"message": "No student was found with that enrollment ID."}), 401
    session.clear()
    session["student_id"] = student[0]
    session["username"] = student[1]
    session["role"] = "student_readonly"
    return jsonify({"message": "Sign-in successful.", "student": {
        "id": student[0], "name": student[1]
    }})


@app.post("/api/student/account/login")
def student_account_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = data.get("password", "")
    if not username or not isinstance(password, str) or not password:
        return jsonify({"message": "Enter your username and password."}), 400
    try:
        user = check_login(username, password)
    except Exception:
        app.logger.exception("Could not check student login")
        return jsonify({"message": "Student account login is unavailable."}), 503
    if not user or user["role"] != "student":
        return jsonify({"message": "Username or password is incorrect."}), 401
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT student_id FROM users WHERE id = %s", (user["id"],))
        student_row = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    if not student_row or not student_row[0]:
        return jsonify({"message": "This account is not connected to a student record."}), 400
    student = get_student(student_row[0])
    if not student:
        return jsonify({"message": "The linked student record was not found."}), 404
    session.clear()
    session["user_id"] = user["id"]
    session["student_id"] = student[0]
    session["username"] = user["username"]
    session["role"] = "student"
    return jsonify({"message": "Sign-in successful.", "student": {
        "id": student[0], "name": student[1]
    }})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "Signed out."})


@app.get("/api/me")
@login_required
def current_user():
    return jsonify({
        "username": session.get("username"),
        "role": session.get("role"),
        "student_id": session.get("student_id"),
    })


@app.post("/api/users")
@role_required("admin")
def add_user():
    data = request.get_json(silent=True) or {}
    try:
        user_id = create_user(
            str(data.get("username", "")),
            str(data.get("password", "")),
            str(data.get("role", "student")),
            str(data.get("email", "")),
            data.get("student_id"),
        )
        return jsonify({"message": "User created.", "user_id": user_id}), 201
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except Exception:
        app.logger.exception("Could not create user")
        return jsonify({"message": "Could not create user. Check the database migration and account details."}), 400


@app.get("/api/users")
@role_required("admin")
def users_list():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT users.id, users.username, users.email, users.student_id, users.active, roles.name AS role "
            "FROM users JOIN roles ON roles.id = users.role_id ORDER BY users.username"
        )
        return jsonify({"users": cursor.fetchall()})
    finally:
        cursor.close()
        connection.close()


@app.get("/api/students")
@role_required("admin", "reviewer")
def students_list():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, registered_on, student_number, email, class_name FROM students ORDER BY name")
        return jsonify({"students": cursor.fetchall()})
    finally:
        cursor.close()
        connection.close()


@app.post("/api/students/register-face")
@role_required("admin")
def queue_student_face():
    student_name = str(request.form.get("student_name", "")).strip()
    image_file = request.files.get("image")
    if not student_name or not image_file or not image_file.filename:
        return jsonify({"message": "Enter a student name and choose an image."}), 400
    extension = os.path.splitext(image_file.filename)[1].lower()
    if extension not in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
        return jsonify({"message": "Choose a JPG, PNG, BMP, or WEBP image."}), 400
    safe_name = re.sub(r"[^A-Za-z0-9 _'-]", "", student_name).strip()
    if not safe_name:
        return jsonify({"message": "Student name must use basic English letters or numbers."}), 400
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id FROM students WHERE name = %s", (student_name,))
        student = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    if not student:
        return jsonify({"message": "Add the student first, then upload their face image."}), 404
    folder = os.path.join(os.path.dirname(__file__), "captured_faces")
    os.makedirs(folder, exist_ok=True)
    image_path = os.path.join(folder, safe_name + extension)
    image_file.save(image_path)
    return jsonify({"message": "Image uploaded for face registration.", "student_id": student[0]}), 201


@app.post("/api/enrollment")
@role_required("admin")
def bulk_enrollment():
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename.lower().endswith(".csv"):
        return jsonify({"message": "Choose a CSV file."}), 400
    import tempfile
    import os as path_tools
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temporary_file:
            temporary_path = temporary_file.name
            uploaded_file.save(temporary_file)
        result = import_students_csv(temporary_path, uploaded_file.filename)
        return jsonify(result), 201
    except Exception:
        app.logger.exception("Student CSV import failed")
        return jsonify({"message": "Could not import the CSV. Check its headers and database migration."}), 400
    finally:
        if temporary_path and path_tools.path.exists(temporary_path):
            path_tools.path.remove(temporary_path)


@app.get("/api/attendance")
@role_required("admin", "reviewer")
def attendance_logs():
    end_date = request.args.get("end_date") or __import__("datetime").date.today().isoformat()
    start_date = request.args.get("start_date") or end_date
    student_id = request.args.get("student_id")
    try:
        rows = get_attendance_rows(start_date, end_date, student_id)
        for row in rows:
            row["attendance_date"] = str(row["attendance_date"])
            row["timestamp"] = str(row["timestamp"])
        return jsonify({"attendance": rows})
    except Exception as error:
        return jsonify({"message": "Enter valid dates and check MySQL."}), 400


@app.get("/api/attendance/summary/<int:student_id>")
@role_required("admin", "reviewer", "student")
def attendance_summary(student_id):
    if session.get("role") == "student" and session.get("student_id") != student_id:
        return jsonify({"message": "You can only view your own attendance."}), 403
    from datetime import date
    end_date = request.args.get("end_date") or date.today().isoformat()
    start_date = request.args.get("start_date") or end_date
    try:
        holidays_in_range = get_holidays(start_date, end_date)
        holidays = [str(item["holiday_date"]) for item in holidays_in_range]
        leave_dates = get_approved_leave_dates(student_id, start_date, end_date)
        working_days = get_working_days(start_date, end_date, holidays, leave_dates)
        records = get_attendance_rows(start_date, end_date, student_id)
        records = [row for row in records if str(row["attendance_date"]) in working_days]
        summary = calculate_attendance_summary(records, working_days)
        summary["absent_dates"] = find_absent_dates(working_days, records)
        return jsonify(summary)
    except Exception:
        return jsonify({"message": "Could not calculate attendance. Check the dates and database migration."}), 400


@app.post("/api/attendance/mark")
@role_required("admin")
def manual_attendance_mark():
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    attendance_date = str(data.get("attendance_date", ""))
    status = str(data.get("status", ""))
    if status not in ("present", "absent", "failed"):
        return jsonify({"message": "Status must be present, absent, or failed."}), 400
    try:
        from datetime import date
        date.fromisoformat(attendance_date)
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO attendance (student_id, timestamp, status) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE status = VALUES(status)",
                (student_id, attendance_date + " 12:00:00", status),
            )
            connection.commit()
            return jsonify({"message": "Attendance saved."})
        finally:
            cursor.close()
            connection.close()
    except Exception:
        app.logger.exception("Could not save attendance")
        return jsonify({"message": "Could not save attendance. Check the student ID and date."}), 400


@app.post("/api/attendance/session/start")
@role_required("admin")
def start_session():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id FROM attendance_sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1")
        active = cursor.fetchone()
        if active:
            return jsonify({"message": "An attendance session is already active.", "session_id": active[0]})
        cursor.execute("INSERT INTO attendance_sessions (started_at, ended_at) VALUES (NOW(), NULL)")
        session_id = cursor.lastrowid
        cursor.execute(
            "INSERT IGNORE INTO attendance (student_id, timestamp, status) "
            "SELECT id, NOW(), 'absent' FROM students"
        )
        connection.commit()
        return jsonify({"message": "Attendance session started.", "session_id": session_id}), 201
    except Exception:
        connection.rollback()
        app.logger.exception("Could not start attendance session")
        return jsonify({"message": "Could not start attendance session."}), 500
    finally:
        cursor.close()
        connection.close()


@app.get("/api/attendance/session")
@role_required("admin", "reviewer")
def attendance_session_status():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id, started_at FROM attendance_sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1")
        active = cursor.fetchone()
        if not active:
            return jsonify({"active": False})
        return jsonify({"active": True, "session_id": active[0], "started_at": str(active[1])})
    finally:
        cursor.close()
        connection.close()


@app.post("/api/attendance/session/stop")
@role_required("admin")
def stop_session():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE attendance_sessions SET ended_at = NOW() WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1")
        connection.commit()
        if cursor.rowcount == 0:
            return jsonify({"message": "There is no active attendance session."}), 404
        return jsonify({"message": "Attendance session stopped."})
    finally:
        cursor.close()
        connection.close()


@app.post("/api/leaves")
@role_required("student")
def new_leave_request():
    data = request.get_json(silent=True) or {}
    try:
        request_id = request_leave(
            session["student_id"], str(data.get("start_date", "")),
            str(data.get("end_date", "")), str(data.get("reason", "")),
        )
        return jsonify({"message": "Leave request sent.", "request_id": request_id}), 201
    except Exception as error:
        return jsonify({"message": str(error)}), 400


@app.get("/api/leaves")
@role_required("admin", "reviewer", "student")
def list_leave_requests():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = (
            "SELECT leave_requests.*, students.name FROM leave_requests "
            "JOIN students ON students.id = leave_requests.student_id"
        )
        values = []
        if session.get("role") == "student":
            query += " WHERE leave_requests.student_id = %s"
            values.append(session["student_id"])
        query += " ORDER BY leave_requests.created_at DESC"
        cursor.execute(query, tuple(values))
        rows = cursor.fetchall()
        for row in rows:
            for key in ("start_date", "end_date", "created_at"):
                row[key] = str(row[key])
        return jsonify({"leave_requests": rows})
    finally:
        cursor.close()
        connection.close()


@app.post("/api/leaves/<int:request_id>/review")
@role_required("admin", "reviewer")
def decide_leave(request_id):
    data = request.get_json(silent=True) or {}
    try:
        changed = review_leave(request_id, session.get("user_id"), str(data.get("decision", "")),
                               str(data.get("note", "")))
        if not changed:
            return jsonify({"message": "Request was not found or has already been reviewed."}), 404
        return jsonify({"message": "Leave request updated."})
    except ValueError as error:
        return jsonify({"message": str(error)}), 400


@app.route("/api/holidays", methods=["GET", "POST"])
@role_required("admin", "reviewer")
def holiday_list_or_add():
    if request.method == "GET":
        from datetime import date
        start = request.args.get("start_date", date.today().replace(month=1, day=1).isoformat())
        end = request.args.get("end_date", date.today().replace(month=12, day=31).isoformat())
        try:
            return jsonify({"holidays": get_holidays(start, end)})
        except Exception:
            return jsonify({"message": "Enter valid dates."}), 400
    if session.get("role") != "admin":
        return jsonify({"message": "Only an admin can add holidays."}), 403
    data = request.get_json(silent=True) or {}
    try:
        holiday_id = add_holiday(str(data.get("holiday_date", "")), str(data.get("name", "")))
        return jsonify({"message": "Holiday added.", "holiday_id": holiday_id}), 201
    except Exception as error:
        return jsonify({"message": str(error)}), 400


@app.get("/api/notifications")
@login_required
def notification_list():
    if not session.get("user_id"):
        return jsonify({"notifications": []})
    only_unread = request.args.get("unread", "false").lower() == "true"
    return jsonify({"notifications": get_notifications(session["user_id"], only_unread)})


@app.post("/api/notifications")
@role_required("admin", "reviewer")
def notification_send():
    data = request.get_json(silent=True) or {}
    try:
        notification_id = send_notification(int(data.get("user_id")), str(data.get("message", "")),
                                            str(data.get("channel", "in_app")))
        return jsonify({"message": "Notification saved.", "notification_id": notification_id}), 201
    except Exception as error:
        return jsonify({"message": str(error)}), 400


@app.post("/api/notifications/<int:notification_id>/read")
@login_required
def notification_read(notification_id):
    if not session.get("user_id"):
        return jsonify({"message": "User account required."}), 403
    changed = mark_notification_read(notification_id, session["user_id"])
    return jsonify({"message": "Notification marked read." if changed else "Notification not found."}), 200 if changed else 404


@app.post("/api/password/forgot")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    if not email:
        return jsonify({"message": "Enter your account email."}), 400
    try:
        token = create_reset_token(email)
        result = {"message": "If the account exists, a reset token has been created."}
        if token and os.getenv("FACE_SHOW_RESET_TOKEN") == "1":
            result["development_token"] = token
        return jsonify(result)
    except Exception:
        app.logger.exception("Could not create password reset token")
        return jsonify({"message": "Password reset is unavailable. Check the database migration."}), 503


@app.post("/api/password/reset")
def change_password_with_token():
    data = request.get_json(silent=True) or {}
    try:
        changed = reset_password(str(data.get("token", "")), str(data.get("new_password", "")))
        if not changed:
            return jsonify({"message": "That token is invalid or expired."}), 400
        return jsonify({"message": "Password updated."})
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except Exception:
        app.logger.exception("Could not reset password")
        return jsonify({"message": "Password reset is unavailable."}), 503


if __name__ == "__main__":
    port = int(os.getenv("FACE_API_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
