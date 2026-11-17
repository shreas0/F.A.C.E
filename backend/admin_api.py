
import os
import sys

from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from passwords import verify_password


app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"service": "admin_api", "status": "ok"})


def get_database():
    """Load the database connection only when a login request needs it."""
    try:
        from database import Database
        return Database
    except Exception:
        app.logger.exception("Could not connect to the attendance database")
        return None


@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = data.get("password", "")

    if not username or not isinstance(password, str) or not password:
        return jsonify({"message": "Enter your admin ID and password."}), 400

    database = get_database()
    if database is None:
        return jsonify({"message": "The login API is running, but MySQL is unavailable. Start MySQL in XAMPP and confirm it uses port 3306."}), 503

    admin = database.read_admin(username)
    if not admin:
        app.logger.warning("Admin sign-in failed: username %r was not found", username)
        return jsonify({"message": "Admin ID or password is incorrect."}), 401

    if not verify_password(password, admin[2]):
        app.logger.warning("Admin sign-in failed: incorrect password for %r", username)
        return jsonify({"message": "Admin ID or password is incorrect."}), 401

    return jsonify({"message": "Sign-in successful.", "admin": {
        "id": admin[0],
        "username": admin[1],
    }})


@app.route("/api/student/login", methods=["POST"])
def student_login():
    data = request.get_json(silent=True) or {}
    student_id = str(data.get("student_id", "")).strip()

    if not student_id.isdigit():
        return jsonify({"message": "Enter a valid student enrollment ID."}), 400

    database = get_database()
    if database is None:
        return jsonify({"message": "The login API is running, but MySQL is unavailable. Start MySQL in XAMPP and confirm it uses port 3306."}), 503

    student = database.get_student(student_id)
    if not student:
        return jsonify({"message": "No student was found with that enrollment ID."}), 401

    return jsonify({"message": "Sign-in successful.", "student": {
        "id": student[0],
        "name": student[1],
    }})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
