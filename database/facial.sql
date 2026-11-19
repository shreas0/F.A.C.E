CREATE DATABASE IF NOT EXISTS facial_attendance;
DROP TABLE IF exists admins;
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS students;

USE facial_attendance;
-- ---------------------------------------------------------------------
-- Table: roles
-- ---------------------------------------------------------------------
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(30) NOT NULL
);
CREATE TABLE IF NOT EXISTS USERS (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id       INT,
    created_on    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP

) ENGINE=InnoDB;
CREATE TABLE password_reset_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    CONSTRAINT fk_password_reset_user
        FOREIGN KEY (user_id)
        REFERENCES admins(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
CREATE TABLE enrollment_batches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uploaded_by INT,
    file_name VARCHAR(255),
    total_records INT,
    successful_records INT,
    uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- ---------------------------------------------------------------------
-- Table: students
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    roll_no			VARCHAR(100) NOT NULL,
    face_encoding   BLOB,
    registered_on   INT NOT NULL,
    CONSTRAINT fk_students_registered_on
        FOREIGN KEY (registered_on)
        REFERENCES USERS(role_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    
    CONSTRAINT uq_student_name UNIQUE (name)
) ENGINE=InnoDB;
-- ---------------------------------------------------------------------
-- Table: attendance
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    student_id        INT NOT NULL,
    DATE			  DATE,
    timestamp         DATETIME NOT NULL,
    attendance_date   DATE GENERATED ALWAYS AS (DATE(timestamp)) STORED,
    status            ENUM('present', 'failed') NOT NULL DEFAULT 'present',
    liveness_score    FLOAT,
    CONSTRAINT fk_attendance_student
        FOREIGN KEY (student_id) REFERENCES students(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_student_per_day
        UNIQUE (student_id, attendance_date)
) ENGINE=InnoDB;
CREATE TABLE leave_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason TEXT,
    status ENUM('pending','approved','rejected') DEFAULT 'pending',
    reviewed_by INT,
    requested_on DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE holidays (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    description VARCHAR(255)
);
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    message VARCHAR(255),
    sent_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    channel ENUM('email','sms','app')
);
