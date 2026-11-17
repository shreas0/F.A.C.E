import csv
import os

from feature_database import get_connection


def import_students_csv(file_path, original_file_name=None):
    with open(file_path, "r", encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    connection = get_connection()
    cursor = connection.cursor()
    successful = 0
    try:
        cursor.execute(
            "INSERT INTO enrollment_batches (file_name, total_records) VALUES (%s, %s)",
            (original_file_name or os.path.basename(file_path), len(rows)),
        )
        batch_id = cursor.lastrowid
        for row in rows:
            student_number = (row.get("student_number") or "").strip()
            name = (row.get("name") or "").strip()
            if not student_number or not name:
                continue
            cursor.execute(
                "INSERT IGNORE INTO students (name, face_encoding, registered_on, student_number, email, class_name) "
                "VALUES (%s, %s, NOW(), %s, %s, %s)",
                (name, "[]", student_number, (row.get("email") or "").strip(),
                 (row.get("class_name") or "").strip()),
            )
            if cursor.rowcount == 1:
                successful += 1
            else:
                cursor.execute(
                    "UPDATE students SET student_number = %s, email = %s, class_name = %s "
                    "WHERE name = %s AND student_number IS NULL",
                    (student_number, (row.get("email") or "").strip(),
                     (row.get("class_name") or "").strip(), name),
                )
                successful += cursor.rowcount
        cursor.execute(
            "UPDATE enrollment_batches SET successful_records = %s WHERE id = %s",
            (successful, batch_id),
        )
        connection.commit()
        return {"batch_id": batch_id, "total_records": len(rows), "successful_records": successful}
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
