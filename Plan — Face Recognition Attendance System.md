# Plan — Face Recognition Attendance System

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

## Out of MVP Scope

The following features are not part of the initial implementation:

- Role-based access control
- Bulk enrollment
- Leave requests
- Holiday calendar
- Notifications
- Forgot password
- Encryption

These features will be documented as possible future improvements in the project report rather than being implemented during the MVP.

## Goal

The main goal is to create a working **end-to-end attendance pipeline**:

**Camera → Face Recognition → Student Identification → Attendance Check → Mark Attendance → View Attendance Log**

The priority is to get this complete pipeline working reliably before adding additional features or complexity.