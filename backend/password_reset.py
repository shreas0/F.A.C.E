from datetime import datetime, timedelta
import hashlib
import secrets

from feature_database import get_connection
from roles import _hash_password


def create_reset_token(email, minutes_valid=30):
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now() + timedelta(minutes=minutes_valid)
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s AND active = 1", (email.lower(),))
        user = cursor.fetchone()
        if user is None:
            return None
        cursor.execute(
            "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
            (user[0], token_hash, expires_at),
        )
        connection.commit()
        return token
    finally:
        cursor.close()
        connection.close()


def reset_password(token, new_password):
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, user_id FROM password_reset_tokens WHERE token_hash = %s "
            "AND used_at IS NULL AND expires_at > NOW() FOR UPDATE",
            (token_hash,),
        )
        row = cursor.fetchone()
        if row is None:
            return False
        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                       (_hash_password(new_password), row["user_id"]))
        cursor.execute("UPDATE password_reset_tokens SET used_at = NOW() WHERE id = %s", (row["id"],))
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
