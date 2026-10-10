CREATE DATABASE IF NOT EXISTS facial_attendance;
USE facial_attendance;
DROP TABLE IF exists admins;
DROP TABLE IF EXISTS attendance_sessions;
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS students;


-- ---------------------------------------------------------------------
-- Table: admins
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admins (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_on    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP

) ENGINE=InnoDB;
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
    status            ENUM('absent', 'present', 'failed') NOT NULL DEFAULT 'absent',
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
