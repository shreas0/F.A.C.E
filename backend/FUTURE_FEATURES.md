# F.A.C.E role access

The API in `main.py` protects each workflow on the server. The React route
guards mirror the permissions for easier navigation, but do not replace API
authorization.

| Role | Workflows |
|---|---|
| `admin` | User management, enrollment, face registration, attendance, sessions, leave review, holidays, notifications |
| `hod` | School-wide students and attendance, sessions, enrollment, leave review, holidays, notifications |
| `teacher` | Students and attendance within the account's assigned `class_name`, and leave review within that class |
| `staff` | Student enrollment, face registration, attendance records and marking, sessions, notifications |
| `reviewer` | Attendance reports and leave request review |
| `student` | Own attendance, leave requests, and notifications |
| `parent` | Attendance, leave requests, and notifications for the linked student |

The standalone schema is `database/facial.sql`; feature tables, accounts, and roles are added by
`database/future_features.sql`. On an existing installation, run
`database/migrate_role_access.sql` and `database/migrate_attendance_absent.sql`
to add the new role names, class field, and `late` attendance status.
Seed disposable local accounts with `python backend/seed_test_accounts.py`.

The current version uses FaceNet recognition with one attendance row per
student per day. It does not perform liveness checks. The student test account
links to a demo student without a registered face; upload a test image for that
student through the admin enrollment screen to exercise the camera recognition
path.
