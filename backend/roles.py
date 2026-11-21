import secrets

from passwords import ITERATIONS
from passwords import verify_password
from feature_database import get_connection


def _hash_password(password):
    import hashlib

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


SUPPORTED_ROLES = {"admin", "hod", "teacher", "staff", "reviewer", "student", "parent"}


def create_user(username, password, role_name, email, student_id=None, class_name=None):
    if not username.strip() or not email.strip() or len(password) < 4:
        raise ValueError("Enter a username, email, and password of at least 4 characters")
    role_name = role_name.strip().lower()
    class_name = (class_name or "").strip() or None
    if role_name not in SUPPORTED_ROLES:
        raise ValueError("Choose a supported account role")
    if role_name == "teacher" and not class_name:
        raise ValueError("Assign a class to each teacher account")
    if role_name in ("student", "parent") and not student_id:
        raise ValueError("Link each student or parent account to a student record")
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
        role = cursor.fetchone()
        if role is None:
            raise ValueError("That role does not exist")
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role_id, student_id, class_name) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (username.strip(), email.strip().lower(), _hash_password(password), role[0], student_id, class_name),
        )
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def check_login(username, password):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT users.id, users.username, users.email, users.class_name, roles.name AS role "
            "FROM users JOIN roles ON roles.id = users.role_id "
            "WHERE (users.username = %s OR users.email = %s) AND users.active = 1",
            (username.strip(), username.strip().lower()),
        )
        user = cursor.fetchone()
        if user is None:
            return None
        cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user["id"],))
        password_row = cursor.fetchone()
        if not verify_password(password, password_row["password_hash"]):
            return None
        return user
    finally:
        cursor.close()
        connection.close()


def user_has_role(user_id, role_name):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT 1 FROM users JOIN roles ON roles.id = users.role_id "
            "WHERE users.id = %s AND roles.name = %s AND users.active = 1",
            (user_id, role_name),
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        connection.close()
