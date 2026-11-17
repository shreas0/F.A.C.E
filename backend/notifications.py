from feature_database import get_connection


def send_notification(user_id, message, channel="in_app"):
    if not message.strip():
        raise ValueError("Notification message cannot be empty")
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO notifications (user_id, message, channel) VALUES (%s, %s, %s)",
            (user_id, message.strip(), channel),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        connection.close()


def get_notifications(user_id, unread_only=False):
    query = "SELECT * FROM notifications WHERE user_id = %s"
    if unread_only:
        query += " AND read_at IS NULL"
    query += " ORDER BY created_at DESC"
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, (user_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def mark_notification_read(notification_id, user_id):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE notifications SET read_at = NOW() WHERE id = %s AND user_id = %s AND read_at IS NULL",
            (notification_id, user_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        cursor.close()
        connection.close()
