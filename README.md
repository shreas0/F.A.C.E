# Plan — 

## What It Does

Students approach a camera, and the system identifies their face and automatically records their attendance. No manual roll call is required.

## How It Works

1. **ESP32-CAM** captures two photos and sends them to the server.
2. The **Flask server** compares the detected face with stored student data.
3. If a match is found, the system checks whether attendance has already been recorded for that student today.
4. If attendance has not been recorded, the system saves the attendance.
5. The result is returned by Flask and displayed to the user. An **OLED display** can optionally show the response.

### Flow

`Camera → Face Recognition → Student Match → Duplicate Check → Mark Attendance → Display Result`

## Team Roles

| Person | Role |
|---|---|
| Vishal Verma | Database |
| Satwik Maurya | ML / Face Recognition |
| Siri (Shreshtha Sharma) | File Handling + Attendance Logic |
| All | UI Development after MVP works |

## Tech Stack

### Hardware
- ESP32-CAM (AI-Thinker)
- Plain ESP32
- OLED Display

### Backend
- Python
- Flask

### Face Recognition
- MediaPipe Face Mesh
- Face distance comparison

### Database
- MySQL

### Frontend
- React
- React communicates directly with the Flask API

## Core Functions

The system will provide the following basic functionality:

- Add or retrieve admin
- Add students and retrieve student data
- Check whether attendance has already been recorded today
- Mark attendance
- Retrieve attendance logs
- Filter attendance logs by date or student

## Key Decisions for MVP

The first version will intentionally remain simple so that the complete pipeline can be built and tested quickly.

- **Registration:** Only admins can register students. Students cannot register themselves.
- **Attendance Deduplication:** A student can have only one attendance entry per day.
- **Login:** Session-cookie based login without a "Remember Me" option.
- **ESP32 Communication:** No push notification system will be implemented. The OLED simply displays the response received from Flask.
- **Liveness / Anti-Proxy Detection:** Blink or iris-based detection will be considered later once the required hardware is available.

## Access by Role

| Role | Access |
|---|---|
| Admin | Manage users, enrollment, face registration, attendance sessions, records, holidays, leave reviews, and notifications |
| HOD | School-wide attendance and student oversight, sessions, enrollment, holidays, leave reviews, and notifications |
| Teacher | Attendance and leave review for the teacher's assigned class |
| Staff | Daily attendance, enrollment, session controls, student lists, and notifications |
| Reviewer | View attendance and review leave requests |
| Student | View their own attendance and notifications, and request leave |
| Parent | View the linked student's attendance and notifications, and request leave |

API permissions are enforced on the server; frontend route guards are only a second
layer. Teacher accounts must have an assigned class. HOD access is school-wide
because the current schema has no separate department table.

Face liveness checks and encryption of stored face embeddings remain out of the
current build. The camera uses face recognition and daily duplicate prevention.

These features will be documented as possible future improvements in the project report rather than being implemented during the MVP.

## Goal

The main goal is to create a working **end-to-end attendance pipeline**:

**Camera → Face Recognition → Student Identification → Attendance Check → Mark Attendance → View Attendance Log**

## Test Accounts

After MySQL is running and the schema migrations are applied, seed local-only
accounts for every role:

```text
python backend/seed_test_accounts.py
```

| Role | Username | Password |
|---|---|---|
| Admin | `000` | `just4test` |
| HOD | `test.hod` | `HodTest123!` |
| Teacher (class Demo) | `test.teacher` | `TeacherTest123!` |
| Staff | `test.staff` | `StaffTest123!` |
| Reviewer | `test.reviewer` | `ReviewerTest123!` |
| Student (Demo Student) | `test.student` | `StudentTest123!` |
| Parent (Demo Student) | `test.parent` | `ParentTest123!` |

The seed is repeatable and resets these demo account passwords each time. These
credentials are for local testing only. To test teacher scoping, use the seeded
`Demo` class and `Demo Student` record.

For an existing database that has already run `database/future_features.sql`,
run `database/migrate_role_access.sql` and
`database/migrate_attendance_absent.sql` to add the new roles/class field and
the `late` attendance status. For a fresh database, run `database/facial.sql`
followed by `database/future_features.sql`.

Install backend packages with `pip install -r backend/requirements.txt`, start
the APIs with `backend/run_backend.bat`, and start React from
`frontend/facial_attendance_capture_engine` with `npm start`. The frontend sends
requests to Flask; it never connects directly to MySQL.

The priority is to get this complete pipeline working reliably before adding additional features or complexity.
