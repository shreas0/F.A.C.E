USE facial_attendance;

-- Test login: username (admin ID) 000, password just4test.
-- The stored value is a salted PBKDF2-SHA256 hash, not the plain password.
INSERT INTO admins (username, password_hash)
VALUES (
    '000',
    'pbkdf2_sha256$600000$622e16b9ac1fcce4510fd5a09d659ee9$4200222f2f7e4792591595dcbc5af4d3de505985390e3f7cab4695ab809b369c'
)
ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash);
