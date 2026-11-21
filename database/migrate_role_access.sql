USE facial_attendance;

CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255) NOT NULL DEFAULT ''
) ENGINE=InnoDB;

INSERT IGNORE INTO roles (name, description) VALUES
    ('admin', 'System administrator'),
    ('hod', 'School-wide attendance and leave oversight'),
    ('teacher', 'Attendance access for assigned class'),
    ('staff', 'Daily attendance and enrollment operations'),
    ('reviewer', 'Reviews student leave requests'),
    ('student', 'Student account'),
    ('parent', 'Parent or guardian account');

-- MySQL does not support ADD COLUMN IF NOT EXISTS on every version shipped
-- with XAMPP, so prepare the ALTER only when the column is missing.
SET @has_class_name = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'class_name'
);
SET @class_name_ddl = IF(
    @has_class_name = 0,
    'ALTER TABLE users ADD COLUMN class_name VARCHAR(100) NULL',
    'SELECT 1'
);
PREPARE class_name_stmt FROM @class_name_ddl;
EXECUTE class_name_stmt;
DEALLOCATE PREPARE class_name_stmt;
