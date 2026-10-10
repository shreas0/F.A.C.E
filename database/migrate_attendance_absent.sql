-- Run once against an existing facial_attendance database before using the
-- updated registration and recognition flow.
ALTER TABLE attendance
    MODIFY status ENUM('absent', 'present', 'failed') NOT NULL DEFAULT 'absent';

CREATE TABLE IF NOT EXISTS attendance_sessions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    started_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at    DATETIME NULL
) ENGINE=InnoDB;
