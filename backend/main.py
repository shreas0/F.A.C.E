import json
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
from passwords import hash_password, verify_password
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
CORS(
    app,
    supports_credentials=True,
    origins=[origin.strip() for origin in os.getenv(
        "FACE_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",") if origin.strip()],
)


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
        cursor.execute("SELECT id, name, class_name FROM students WHERE id = %s", (student_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def can_access_student(student_id):
    """Keep teacher attendance and student views within their assigned class."""
    role = session.get("role")
    if role in ("student", "parent"):
        return int(session.get("student_id", -1)) == int(student_id)
    if role != "teacher":
        return True
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT students.id FROM students JOIN users ON users.class_name = students.class_name "
            "WHERE students.id = %s AND users.id = %s AND users.active = 1",
            (student_id, session.get("user_id")),
        )
        return cursor.fetchone() is not None
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
        if session.get("role") == "teacher":
            query += " AND students.class_name = (SELECT class_name FROM users WHERE id = %s)"
            values.append(session.get("user_id"))
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
        return jsonify({"message": "Enter your work account and password."}), 400

    try:
        user = check_login(username, password)
        if (not user or user["role"] not in ("admin", "hod", "teacher", "staff", "reviewer")) and "." not in username:
            for suffix in ("admin", "staff", "hod", "teacher", "reviewer"):
                candidate = check_login(f"{username}.{suffix}", password)
                if candidate and candidate["role"] in ("admin", "hod", "teacher", "staff", "reviewer"):
                    user = candidate
                    break
        if user and user["role"] in ("admin", "hod", "teacher", "staff", "reviewer"):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["class_name"] = user.get("class_name")
            return jsonify({"message": "Sign-in successful.", "admin": {
                "id": user["id"], "username": user["username"], "role": user["role"]
            }})
    except Exception:
        app.logger.exception("Role login failed; trying the legacy admin table")

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


@app.post("/api/student/account/login")
def student_account_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = data.get("password", "")
    if not username or not isinstance(password, str) or not password:
        return jsonify({"message": "Enter your username and password."}), 400
    try:
        user = check_login(username, password)
        if (not user or user["role"] not in ("student", "parent")) and "." not in username:
            candidate = check_login(f"{username}.student", password)
            if candidate and candidate["role"] in ("student", "parent"):
                user = candidate
    except Exception:
        app.logger.exception("Could not check student login")
        return jsonify({"message": "Student account login is unavailable."}), 503
    if not user or user["role"] not in ("student", "parent"):
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
    session["role"] = user["role"]
    return jsonify({"message": "Sign-in successful.", "student": {
        "id": student[0], "name": student[1]
    }})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "Signed out."})


@app.post("/api/auth/single-login")
def single_login():
    """Unified login endpoint: automatically formats username with post and routes to appropriate dashboard."""
    data = request.get_json(silent=True) or {}
    user_id = str(data.get("user_id") or data.get("username") or "").strip()
    post = str(data.get("post") or data.get("role") or "").strip().lower()
    password = data.get("password", "")

    if not user_id or not isinstance(password, str) or not password:
        return jsonify({"message": "Enter your User ID and password."}), 400

    # Build candidate usernames to try:
    candidates = []
    if post:
        if user_id.endswith(f".{post}"):
            candidates.append(user_id)
        else:
            candidates.append(f"{user_id}.{post}")
    candidates.append(user_id)

    authenticated_user = None
    for candidate in candidates:
        user = check_login(candidate, password)
        if user:
            # If a post was chosen, verify it matches
            if post and user["role"] != post:
                continue
            authenticated_user = user
            break

    # If post was admin or empty, also check legacy admins table
    if not authenticated_user:
        for candidate in candidates:
            admin = Database.read_admin(candidate)
            if admin and verify_password(password, admin[2]):
                authenticated_user = {
                    "id": admin[0],
                    "username": admin[1],
                    "role": "admin",
                    "class_name": None,
                }
                break

    if not authenticated_user:
        return jsonify({"message": "Invalid User ID, Post, or Password."}), 401

    session.clear()
    session["user_id"] = authenticated_user["id"]
    session["username"] = authenticated_user["username"]
    session["role"] = authenticated_user["role"]
    session["class_name"] = authenticated_user.get("class_name")

    student_id = None
    if authenticated_user["role"] in ("student", "parent"):
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT student_id FROM users WHERE id = %s", (authenticated_user["id"],))
            row = cur.fetchone()
            if row and row[0]:
                student_id = row[0]
                session["student_id"] = student_id
        finally:
            cur.close()
            conn.close()

    role = authenticated_user["role"]
    if role == "admin":
        redirect_url = "/Dashboard/Admin"
    elif role in ("staff", "hod", "teacher", "reviewer"):
        redirect_url = "/Dashboard/Staff"
    else:
        redirect_url = "/Dashboard/Student"

    return jsonify({
        "message": f"Sign-in successful as {role.upper()}.",
        "user": {
            "id": authenticated_user["id"],
            "username": authenticated_user["username"],
            "role": authenticated_user["role"],
            "student_id": student_id,
            "class_name": authenticated_user.get("class_name"),
        },
        "redirect": redirect_url,
    })


@app.get("/api/candidates/permissions")
@role_required("admin", "hod", "staff")
def candidate_registration_permissions():
    """Return which candidate posts the currently logged-in user is allowed to register."""
    current_role = session.get("role")
    if current_role == "admin":
        allowed = [
            {"post": "student", "label": "Student"},
            {"post": "teacher", "label": "Teacher"},
            {"post": "staff", "label": "Staff"},
            {"post": "hod", "label": "Head of Department (HOD)"},
            {"post": "reviewer", "label": "Leave Reviewer"},
            {"post": "parent", "label": "Parent / Guardian"},
            {"post": "admin", "label": "Administrator"},
        ]
    elif current_role == "hod":
        allowed = [
            {"post": "teacher", "label": "Teacher"},
            {"post": "student", "label": "Student"},
            {"post": "reviewer", "label": "Leave Reviewer"},
        ]
    elif current_role == "staff":
        allowed = [
            {"post": "student", "label": "Student"},
        ]
    else:
        allowed = []
    return jsonify({
        "current_role": current_role,
        "allowed_posts": allowed,
    })


@app.post("/api/candidates/register")
@role_required("admin", "hod", "staff")
def register_candidate():
    """Register any candidate based on post, automatically formatting User ID with post suffix."""
    current_role = session.get("role")

    if request.content_type and "multipart/form-data" in request.content_type:
        full_name = str(request.form.get("full_name") or request.form.get("name") or "").strip()
        user_id = str(request.form.get("user_id") or request.form.get("candidate_id") or "").strip()
        post = str(request.form.get("post") or request.form.get("role") or "").strip().lower()
        email = str(request.form.get("email") or "").strip()
        password = str(request.form.get("password") or "0000").strip()
        class_name = str(request.form.get("class_name") or "").strip() or None
        linked_student_id = request.form.get("linked_student_id")
        face_file = request.files.get("face_image")
    else:
        data = request.get_json(silent=True) or {}
        full_name = str(data.get("full_name") or data.get("name") or "").strip()
        user_id = str(data.get("user_id") or data.get("candidate_id") or "").strip()
        post = str(data.get("post") or data.get("role") or "").strip().lower()
        email = str(data.get("email") or "").strip()
        password = str(data.get("password") or "0000").strip()
        class_name = str(data.get("class_name") or "").strip() or None
        linked_student_id = data.get("linked_student_id")
        face_file = None

    if not full_name or not user_id or not post:
        return jsonify({"message": "Full Name, User ID, and Post are required."}), 400

    if current_role == "admin":
        allowed_posts = {"student", "teacher", "staff", "hod", "reviewer", "parent", "admin"}
    elif current_role == "hod":
        allowed_posts = {"teacher", "student", "reviewer"}
    elif current_role == "staff":
        allowed_posts = {"student"}
    else:
        return jsonify({"message": "You do not have permission to register candidates."}), 403

    if post not in allowed_posts:
        return jsonify({"message": f"Your role ({current_role.upper()}) is not allowed to register a {post.upper()}."}), 403

    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", user_id)
    if not safe_id:
        return jsonify({"message": "Enter a valid numeric or alphanumeric User ID."}), 400

    # Auto-format username with post: e.g. 2342.student or 2342.hod
    if safe_id.endswith(f".{post}"):
        final_username = safe_id
    else:
        final_username = f"{safe_id}.{post}"

    if not email:
        email = f"{final_username}@face.local"

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Check if username or email already exists
        cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (final_username, email))
        if cur.fetchone():
            return jsonify({"message": f"Account with User ID '{final_username}' or email '{email}' already exists."}), 400

        cur.execute("SELECT id FROM roles WHERE name = %s", (post,))
        role_row = cur.fetchone()
        if not role_row:
            return jsonify({"message": f"Role '{post}' does not exist in the database."}), 400
        role_id = role_row[0]

        created_student_id = None

        if post == "student":
            encoding_json = "[]"
            if face_file and face_file.filename:
                ext = os.path.splitext(face_file.filename)[1].lower()
                if ext in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
                    faces_folder = os.path.join(os.path.dirname(__file__), "captured_faces")
                    os.makedirs(faces_folder, exist_ok=True)
                    img_path = os.path.join(faces_folder, f"{full_name}{ext}")
                    face_file.save(img_path)
                    try:
                        from deepface import DeepFace
                        emb_objs = DeepFace.represent(img_path=img_path, model_name="Facenet", enforce_detection=False)
                        if emb_objs and len(emb_objs) > 0:
                            encoding_json = json.dumps(list(emb_objs[0]["embedding"]))
                    except Exception as e:
                        app.logger.warning("Could not extract face embedding for student candidate: %s", e)

            # Insert or update student record
            cur.execute("SELECT id FROM students WHERE name = %s OR student_number = %s", (full_name, safe_id))
            existing_student = cur.fetchone()
            if existing_student:
                created_student_id = existing_student[0]
                cur.execute(
                    "UPDATE students SET student_number = %s, email = %s, class_name = %s, face_encoding = %s WHERE id = %s",
                    (safe_id, email, class_name, encoding_json, created_student_id),
                )
            else:
                cur.execute(
                    "INSERT INTO students (name, face_encoding, registered_on, student_number, email, class_name) "
                    "VALUES (%s, %s, NOW(), %s, %s, %s)",
                    (full_name, encoding_json, safe_id, email, class_name),
                )
                created_student_id = cur.lastrowid

        elif post == "teacher":
            if not class_name:
                return jsonify({"message": "Assigned class is required for teachers."}), 400

        elif post == "parent":
            if linked_student_id:
                try:
                    created_student_id = int(linked_student_id)
                except ValueError:
                    pass

        hashed_pw = hash_password(password)
        cur.execute(
            "INSERT INTO users (username, email, password_hash, role_id, student_id, class_name, active) "
            "VALUES (%s, %s, %s, %s, %s, %s, 1)",
            (final_username, email, hashed_pw, role_id, created_student_id, class_name),
        )
        new_user_id = cur.lastrowid

        if post == "admin":
            cur.execute(
                "INSERT INTO admins (username, password_hash) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash)",
                (safe_id, hashed_pw),
            )
            cur.execute(
                "INSERT INTO admins (username, password_hash) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash)",
                (final_username, hashed_pw),
            )

        conn.commit()
        return jsonify({
            "message": f"Candidate '{full_name}' successfully registered as {post.upper()} with User ID '{final_username}'!",
            "username": final_username,
            "role": post,
            "user_id": new_user_id,
            "student_id": created_student_id,
        }), 201

    except Exception:
        conn.rollback()
        app.logger.exception("Candidate registration failed")
        return jsonify({"message": "Candidate registration failed. Check database connection and inputs."}), 500
    finally:
        cur.close()
        conn.close()


@app.get("/api/me")
@login_required
def current_user():
    return jsonify({
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "role": session.get("role"),
        "student_id": session.get("student_id"),
        "class_name": session.get("class_name"),
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
            data.get("class_name"),
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
            "SELECT users.id, users.username, users.email, users.student_id, users.class_name, "
            "users.active, roles.name AS role "
            "FROM users JOIN roles ON roles.id = users.role_id ORDER BY users.username"
        )
        return jsonify({"users": cursor.fetchall()})
    finally:
        cursor.close()
        connection.close()


@app.get("/api/students")
@role_required("admin", "hod", "staff", "teacher", "reviewer")
def students_list():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = "SELECT id, name, registered_on, student_number, email, class_name FROM students"
        values = ()
        if session.get("role") == "teacher":
            query += " WHERE class_name = (SELECT class_name FROM users WHERE id = %s)"
            values = (session.get("user_id"),)
        query += " ORDER BY name"
        cursor.execute(query, values)
        return jsonify({"students": cursor.fetchall()})
    finally:
        cursor.close()
        connection.close()


@app.post("/api/students/register-face")
@role_required("admin", "hod", "staff")
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

    # Immediately compute face embedding and save to MySQL database
    try:
        from deepface import DeepFace
        emb_objs = DeepFace.represent(
            img_path=image_path, model_name="Facenet", enforce_detection=False
        )
        if emb_objs and len(emb_objs) > 0:
            new_embedding = emb_objs[0]["embedding"]
            enc_json = json.dumps(list(new_embedding))
            update_conn = get_connection()
            update_cur = update_conn.cursor()
            try:
                update_cur.execute("UPDATE students SET face_encoding = %s WHERE id = %s", (enc_json, student[0]))
                update_conn.commit()
            finally:
                update_cur.close()
                update_conn.close()
            return jsonify({"message": f"Face registered successfully for {student_name}.", "student_id": student[0]}), 201
        else:
            return jsonify({"message": "No face could be detected in the image. Please upload a clearer photo."}), 400
    except Exception as exc:
        app.logger.warning("Immediate face embedding generation failed: %s", exc)
        return jsonify({"message": "Image saved. Face registration is being processed.", "student_id": student[0]}), 201


@app.post("/api/enrollment")
@role_required("admin", "hod", "staff")
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
@role_required("admin", "hod", "staff", "teacher", "reviewer")
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


@app.get("/api/attendance/download-pdf")
def download_attendance_pdf():
    """Download attendance records as a styled PDF report."""
    from flask import send_file
    from download_pdf import generate_attendance_pdf
    import tempfile

    student_id = request.args.get("student_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    temp_dir = tempfile.gettempdir()
    temp_pdf = os.path.join(temp_dir, f"attendance_report_{os.getpid()}.pdf")

    try:
        generate_attendance_pdf(
            output_path=temp_pdf,
            student_id=student_id,
            start_date=start_date,
            end_date=end_date,
        )
        return send_file(temp_pdf, as_attachment=True, download_name="attendance_report.pdf")
    except Exception as exc:
        app.logger.exception("Failed to generate PDF")
        return jsonify({"message": "Could not generate attendance PDF."}), 500
        return jsonify({"message": "Enter valid dates and check MySQL."}), 400


@app.get("/api/attendance/summary/<int:student_id>")
@role_required("admin", "hod", "staff", "teacher", "reviewer", "student", "parent")
def attendance_summary(student_id):
    if session.get("role") in ("student", "parent") and session.get("student_id") != student_id:
        return jsonify({"message": "You can only view your own attendance."}), 403
    if not can_access_student(student_id):
        return jsonify({"message": "This student is outside your assigned class."}), 403
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
@role_required("admin", "hod", "staff", "teacher")
def manual_attendance_mark():
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    attendance_date = str(data.get("attendance_date", ""))
    status = str(data.get("status", ""))
    if status not in ("present", "absent", "late", "failed"):
        return jsonify({"message": "Status must be present, absent, late, or failed."}), 400
    try:
        student_id = int(student_id)
    except (TypeError, ValueError):
        return jsonify({"message": "Enter a valid student ID."}), 400
    if not can_access_student(student_id):
        return jsonify({"message": "This student is outside your assigned class."}), 403
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
@role_required("admin", "hod", "staff")
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
@role_required("admin", "hod", "staff", "teacher", "reviewer")
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
@role_required("admin", "hod", "staff")
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
@role_required("student", "parent")
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
@role_required("admin", "hod", "teacher", "staff", "reviewer", "student", "parent")
def list_leave_requests():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = (
            "SELECT leave_requests.*, students.name FROM leave_requests "
            "JOIN students ON students.id = leave_requests.student_id"
        )
        values = []
        if session.get("role") in ("student", "parent"):
            query += " WHERE leave_requests.student_id = %s"
            values.append(session["student_id"])
        elif session.get("role") == "teacher":
            query += " WHERE students.class_name = (SELECT class_name FROM users WHERE id = %s)"
            values.append(session.get("user_id"))
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
@role_required("admin", "hod", "teacher", "reviewer")
def decide_leave(request_id):
    data = request.get_json(silent=True) or {}
    if session.get("role") == "teacher":
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT student_id FROM leave_requests WHERE id = %s", (request_id,))
            row = cursor.fetchone()
        finally:
            cursor.close()
            connection.close()
        if not row or not can_access_student(row[0]):
            return jsonify({"message": "This request is outside your assigned class."}), 403
    try:
        changed = review_leave(request_id, session.get("user_id"), str(data.get("decision", "")),
                               str(data.get("note", "")))
        if not changed:
            return jsonify({"message": "Request was not found or has already been reviewed."}), 404
        return jsonify({"message": "Leave request updated."})
    except ValueError as error:
        return jsonify({"message": str(error)}), 400


@app.route("/api/holidays", methods=["GET", "POST"])
@role_required("admin", "hod", "teacher", "staff", "reviewer", "student", "parent")
def holiday_list_or_add():
    if request.method == "GET":
        from datetime import date
        start = request.args.get("start_date", date.today().replace(month=1, day=1).isoformat())
        end = request.args.get("end_date", date.today().replace(month=12, day=31).isoformat())
        try:
            return jsonify({"holidays": get_holidays(start, end)})
        except Exception:
            return jsonify({"message": "Enter valid dates."}), 400
    if session.get("role") not in ("admin", "hod"):
        return jsonify({"message": "Only an admin or HOD can add holidays."}), 403
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
@role_required("admin", "hod", "staff")
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
