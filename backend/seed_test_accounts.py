"""Create repeatable local-only accounts for exercising each F.A.C.E role."""

from feature_database import get_connection
from passwords import hash_password


TEST_ACCOUNTS = (
    ("000", "face.admin@face.local", "admin", "just4test", None, None),
    ("test.hod", "test.hod@face.local", "hod", "HodTest123!", None, None),
    ("test.teacher", "test.teacher@face.local", "teacher", "TeacherTest123!", None, "Demo"),
    ("test.staff", "test.staff@face.local", "staff", "StaffTest123!", None, None),
    ("test.reviewer", "test.reviewer@face.local", "reviewer", "ReviewerTest123!", None, None),
    ("test.parent", "test.parent@face.local", "parent", "ParentTest123!", None, None),
    ("1234", "1234@face.local", "admin", "0000", None, None),
    ("1234.admin", "1234.admin@face.local", "admin", "0000", None, None),
    ("1234.staff", "1234.staff@face.local", "staff", "0000", None, None),
    ("1234.student", "1234.student@face.local", "student", "0000", 1, "AD5E"),
    ("1234.teacher", "1234.teacher@face.local", "teacher", "0000", None, "AD5E"),
    ("1234.hod", "1234.hod@face.local", "hod", "0000", None, None),
    ("1234.reviewer", "1234.reviewer@face.local", "reviewer", "0000", None, None),
    ("1234.parent", "1234.parent@face.local", "parent", "0000", 1, None),
)


def seed_test_accounts():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT IGNORE INTO students "
            "(name, face_encoding, registered_on, student_number, email, class_name) "
            "VALUES (%s, %s, NOW(), %s, %s, %s)",
            ("Demo Student", "[]", "TEST-001", "test.student@face.local", "Demo"),
        )
        cursor.execute("SELECT id FROM students WHERE student_number = %s", ("TEST-001",))
        student_row = cursor.fetchone()
        if not student_row:
            raise RuntimeError("Could not create the demo student record")
        student_id = student_row[0]

        cursor.execute(
            "INSERT IGNORE INTO roles (name, description) VALUES "
            "('admin', 'System administrator'), ('hod', 'School-wide oversight'), "
            "('teacher', 'Assigned-class attendance'), ('staff', 'Attendance operations'), "
            "('reviewer', 'Leave request reviewer'), ('student', 'Student account'), "
            "('parent', 'Parent or guardian account')"
        )
        for username, email, role_name, password, linked_student_id, class_name in TEST_ACCOUNTS:
            if role_name == "admin":
                # The demonstration student admin ID is also kept in the original table
                # for installations that still use its legacy sign-in fallback.
                cursor.execute(
                    "INSERT INTO admins (username, password_hash) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash)",
                    (username, hash_password(password)),
                )
            cursor.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
            role_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO users "
                "(username, email, password_hash, role_id, student_id, class_name, active) "
                "VALUES (%s, %s, %s, %s, %s, %s, 1) "
                "ON DUPLICATE KEY UPDATE email = VALUES(email), password_hash = VALUES(password_hash), "
                "role_id = VALUES(role_id), student_id = VALUES(student_id), "
                "class_name = VALUES(class_name), active = 1",
            (username, email, hash_password(password), role_id,
                 linked_student_id or (student_id if role_name in ("student", "parent") else None), class_name),
            )

        cursor.execute("SELECT id FROM roles WHERE name = 'student'")
        student_role_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO users "
            "(username, email, password_hash, role_id, student_id, active) "
            "VALUES (%s, %s, %s, %s, %s, 1) "
            "ON DUPLICATE KEY UPDATE email = VALUES(email), password_hash = VALUES(password_hash), "
            "role_id = VALUES(role_id), student_id = VALUES(student_id), active = 1",
            ("test.student", "test.student@face.local", hash_password("StudentTest123!"),
             student_role_id, student_id),
        )
        connection.commit()
        return student_id
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    demo_student_id = seed_test_accounts()
    print(f"Test accounts ready. Demo student ID: {demo_student_id}")
    print("These accounts are for local testing only; do not use them in production.")
