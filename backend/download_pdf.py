"""
F.A.C.E - Download Attendance Record as PDF
Beginner-friendly script to fetch attendance from MySQL and create a PDF report.
"""

import os
import mysql.connector
from datetime import datetime
from fpdf import FPDF


def get_db_connection():
    """Connect to the MySQL database."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "facial_attendance"),
    )


def fetch_attendance(student_id=None, start_date=None, end_date=None):
    """
    Fetch attendance records joined with student information.
    Optionally filter by student_id or date range.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Base SQL query
    query = """
        SELECT 
            attendance.id,
            students.name,
            COALESCE(students.student_number, '-') AS student_number,
            COALESCE(students.class_name, '-') AS class_name,
            attendance.attendance_date,
            attendance.timestamp,
            attendance.status
        FROM attendance
        JOIN students ON students.id = attendance.student_id
        WHERE 1=1
    """
    params = []

    # Optional filter: student ID
    if student_id:
        query += " AND students.id = %s"
        params.append(student_id)

    # Optional filter: start date
    if start_date:
        query += " AND attendance.attendance_date >= %s"
        params.append(start_date)

    # Optional filter: end date
    if end_date:
        query += " AND attendance.attendance_date <= %s"
        params.append(end_date)

    query += " ORDER BY attendance.timestamp DESC"

    cursor.execute(query, tuple(params))
    records = cursor.fetchall()

    cursor.close()
    conn.close()
    return records


def generate_attendance_pdf(output_path="attendance_report.pdf", student_id=None, start_date=None, end_date=None):
    """
    Generate a clean, readable PDF from MySQL attendance records.
    """
    # 1. Fetch data from database
    records = fetch_attendance(student_id=student_id, start_date=start_date, end_date=end_date)

    # 2. Create PDF object (A4 size, portrait, millimeters)
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 3. Document Title
    pdf.set_font("helvetica", "B", 18)
    pdf.set_text_color(30, 41, 59)  # Dark slate color
    pdf.cell(0, 10, text="F.A.C.E. Attendance Report", align="C", new_x="LMARGIN", new_y="NEXT")

    # Subtitle with report generated time
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    pdf.cell(0, 6, text=f"Generated on: {current_time}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 4. Summary boxes
    total_records = len(records)
    present_count = sum(1 for r in records if r["status"].lower() == "present")
    late_count = sum(1 for r in records if r["status"].lower() == "late")
    absent_count = sum(1 for r in records if r["status"].lower() == "absent")

    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(51, 65, 85)
    summary_text = f"Total: {total_records}  |  Present: {present_count}  |  Late: {late_count}  |  Absent: {absent_count}"
    pdf.cell(0, 8, text=summary_text, align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # 5. Table Header
    # Total width of A4 printable area = 210mm - 20mm margins = 190mm
    col_widths = {
        "id": 25,       # Student ID / Number
        "name": 45,     # Student Name
        "class": 25,    # Class
        "date": 30,     # Date
        "time": 35,     # Time
        "status": 30,   # Status
    }

    pdf.set_font("helvetica", "B", 10)
    pdf.set_fill_color(226, 232, 240)  # Light gray header background
    pdf.set_text_color(15, 23, 42)

    pdf.cell(col_widths["id"], 8, text="Student ID", border=1, fill=True, align="C")
    pdf.cell(col_widths["name"], 8, text="Student Name", border=1, fill=True, align="L")
    pdf.cell(col_widths["class"], 8, text="Class", border=1, fill=True, align="C")
    pdf.cell(col_widths["date"], 8, text="Date", border=1, fill=True, align="C")
    pdf.cell(col_widths["time"], 8, text="Time", border=1, fill=True, align="C")
    pdf.cell(col_widths["status"], 8, text="Status", border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

    # 6. Table Rows
    pdf.set_font("helvetica", "", 9)

    if not records:
        pdf.set_text_color(100, 116, 139)
        pdf.cell(190, 10, text="No attendance records found.", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    else:
        for r in records:
            # Color coding for status
            status_text = str(r["status"]).upper()
            if r["status"].lower() == "present":
                pdf.set_text_color(22, 101, 52)   # Green
            elif r["status"].lower() == "late":
                pdf.set_text_color(180, 83, 9)    # Orange
            else:
                pdf.set_text_color(185, 28, 28)   # Red

            date_str = str(r["attendance_date"])
            time_str = r["timestamp"].strftime("%I:%M:%S %p") if isinstance(r["timestamp"], datetime) else str(r["timestamp"])

            # Regular text color for standard columns
            pdf.set_text_color(15, 23, 42)
            pdf.cell(col_widths["id"], 7, text=str(r["student_number"]), border=1, align="C")
            pdf.cell(col_widths["name"], 7, text=str(r["name"]), border=1, align="L")
            pdf.cell(col_widths["class"], 7, text=str(r["class_name"]), border=1, align="C")
            pdf.cell(col_widths["date"], 7, text=date_str, border=1, align="C")
            pdf.cell(col_widths["time"], 7, text=time_str, border=1, align="C")

            # Colored text for status
            if r["status"].lower() == "present":
                pdf.set_text_color(22, 101, 52)
            elif r["status"].lower() == "late":
                pdf.set_text_color(180, 83, 9)
            else:
                pdf.set_text_color(185, 28, 28)
            pdf.cell(col_widths["status"], 7, text=status_text, border=1, align="C", new_x="LMARGIN", new_y="NEXT")

    # 7. Output PDF file
    pdf.output(output_path)
    print(f"Attendance PDF saved successfully at: {os.path.abspath(output_path)}")
    return output_path


# If executed directly (e.g.: python download_pdf.py)
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(current_dir, "attendance_report.pdf")
    generate_attendance_pdf(output_file)
