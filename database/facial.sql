CREATE DATABASE IF NOT EXISTS facial_attendance;
USE facial_attendance;

-- ---------------------------------------------------------------------
-- Table: admins
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admins (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_on    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP

) ENGINE=InnoDB;
-- Sample admin login: username (admin ID) 000, password just4test.
INSERT INTO admins (username, password_hash)
VALUES (
    '000',
    'pbkdf2_sha256$600000$622e16b9ac1fcce4510fd5a09d659ee9$4200222f2f7e4792591595dcbc5af4d3de505985390e3f7cab4695ab809b369c'
)
ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash);
-- ---------------------------------------------------------------------
-- Table: students
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    face_encoding   JSON         NOT NULL,
    registered_on   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_student_name UNIQUE (name)
) ENGINE=InnoDB;
-- ---------------------------------------------------------------------
-- Table: attendance
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    student_id        INT NOT NULL,
    timestamp         DATETIME NOT NULL,
    attendance_date   DATE GENERATED ALWAYS AS (DATE(timestamp)) STORED,
    status            ENUM('absent', 'present', 'late', 'failed') NOT NULL DEFAULT 'absent',
    CONSTRAINT fk_attendance_student
        FOREIGN KEY (student_id) REFERENCES students(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_student_per_day
        UNIQUE (student_id, attendance_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_sessions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    started_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at    DATETIME NULL
) ENGINE=InnoDB;
