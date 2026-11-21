CREATE DATABASE IF NOT EXISTS facial_attendance;
USE facial_attendance;

-- ---------------------------------------------------------------------
-- Table: roles
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE
);

-- ---------------------------------------------------------------------
-- Table: USERS / admins
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS USERS (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id       INT,
    created_on    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS admins (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

-- Sample admin login: username (admin ID) 000, password just4test.
INSERT INTO admins (username, password_hash)
VALUES (
    '000',
    'pbkdf2_sha256$600000$622e16b9ac1fcce4510fd5a09d659ee9$4200222f2f7e4792591595dcbc5af4d3de505985390e3f7cab4695ab809b369c'
)
ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash);

-- ---------------------------------------------------------------------
-- Table: password_reset_tokens
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS password_reset_tokens (
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

-- ---------------------------------------------------------------------
-- Table: enrollment_batches
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS enrollment_batches (
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
    roll_no         VARCHAR(100),
    face_encoding   BLOB,
    registered_on   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
    liveness_score    FLOAT,
    CONSTRAINT fk_attendance_student
        FOREIGN KEY (student_id) REFERENCES students(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_student_per_day
        UNIQUE (student_id, attendance_date)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Table: leave_requests
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS leave_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason TEXT,
    status ENUM('pending','approved','rejected') DEFAULT 'pending',
    reviewed_by INT,
    requested_on DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: holidays
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS holidays (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    description VARCHAR(255)
);

-- ---------------------------------------------------------------------
-- Table: notifications
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    message VARCHAR(255),
    sent_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    channel ENUM('email','sms','app')
);
