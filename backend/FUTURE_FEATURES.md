# F.A.C.E future feature files

These Python functions are connected to the main Flask API in `main.py`. They use the project's MySQL settings (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`). The frontend still needs pages for these options.

Run `run_backend.bat` to start the main API, ESP32 upload API, and student registration watcher. The main API is at `http://localhost:5000`; ESP32 uploads remain at `http://localhost:5001/upload`. The attendance session can now be started or stopped with the main API.

Main API options include `/api/users`, `/api/students`, `/api/attendance`, `/api/attendance/summary/<student_id>`, `/api/attendance/mark`, `/api/attendance/session`, `/api/attendance/session/start`, `/api/attendance/session/stop`, `/api/enrollment`, `/api/leaves`, `/api/holidays`, `/api/notifications`, and `/api/password/forgot` plus `/api/password/reset`. Sign-in uses session cookies. The current student ID-only screen is read-only for the API; use `/api/student/account/login` with a student user account to access student features such as leave requests.

Before using them, back up the database and run `database/future_features.sql` once in MySQL. This adds the new tables and extra student fields and copies existing admins into the new users table while keeping the old `admins` table intact.

The project already has its own face recognition and attendance marking in `backend/recognition.py`. `logic.py` contains date and summary calculations and does not replace that recognition flow.

- `logic.py`: attendance workday, absent date, and percentage calculations.
- `roles.py`: create users, check login details, and check a user's role.
- `enrollment.py`: read a student CSV and record batch counts.
- `leaves.py`: request leave and approve or reject it.
- `holidays.py`: store and look up holidays.
- `notifications.py`: save/read in-app notifications.
- `password_reset.py`: create expiring, one-use password reset tokens.
- `encryption.py`: optional Fernet text encryption. Install `cryptography` and keep `FACE_ENCRYPTION_KEY` private.
- `feature_database.py`: shared MySQL connection helper.

Enrollment CSV headers: `student_number,name,email,class_name`. The sample password reset function returns a token; a future email feature must send it privately to the account owner.
