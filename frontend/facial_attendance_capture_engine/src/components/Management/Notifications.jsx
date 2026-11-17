import { useEffect } from "react";
import { Link } from "react-router-dom";
import { apiRequest, showMessage, showTable } from "../../services/faceApi";

function Notifications() {
    async function loadNotifications() {
        let unread = document.getElementById("unread-only").checked;
        try {
            let result = await apiRequest(`/api/notifications?unread=${unread}`);
            let rows = [];
            for (let item of result.notifications) {
                rows.push([item.id, item.message, item.channel, item.created_at, item.read_at || "Unread"]);
            }
            showTable("notifications-table", ["ID", "Message", "Channel", "Date", "Read"], rows);
            showMessage("notifications-message", `${rows.length} notification(s) found.`);
        } catch (error) {
            showMessage("notifications-message", error.message);
        }
    }

    async function sendNotification(event) {
        event.preventDefault();
        let form = event.target;
        let data = {
            user_id: Number(form.elements.user_id.value),
            message: form.elements.message.value,
            channel: form.elements.channel.value,
        };
        try {
            let result = await apiRequest("/api/notifications", { method: "POST", body: data });
            showMessage("notification-form-message", result.message);
            form.reset();
            loadNotifications();
        } catch (error) {
            showMessage("notification-form-message", error.message);
        }
    }

    async function markRead(event) {
        event.preventDefault();
        let notificationId = event.target.elements.notification_id.value;
        try {
            let result = await apiRequest(`/api/notifications/${notificationId}/read`, { method: "POST" });
            showMessage("notification-read-message", result.message);
            loadNotifications();
        } catch (error) {
            showMessage("notification-read-message", error.message);
        }
    }

    useEffect(function () {
        loadNotifications();
    }, []);

    return (
        <div>
            <h1>Notifications</h1>
            <p><Link to="/Dashboard/Admin">Back to dashboard</Link></p>
            <section>
                <h2>Inbox</h2>
                <label><input type="checkbox" id="unread-only" /> Unread only</label>
                <button type="button" onClick={loadNotifications}>Refresh inbox</button>
                <p id="notifications-message" role="status"></p>
                <div id="notifications-table"></div>
                <form onSubmit={markRead}>
                    <label>Notification ID <input type="number" name="notification_id" required /></label>
                    <button type="submit">Mark read</button>
                </form>
                <p id="notification-read-message" role="status"></p>
            </section>
            <section>
                <h2>Send an in-app notification</h2>
                <form onSubmit={sendNotification}>
                    <label>User ID <input type="number" name="user_id" required /></label>
                    <label>Message <textarea name="message" required /></label>
                    <label>Channel
                        <select name="channel">
                            <option value="in_app">In app</option>
                            <option value="email">Email (saved only)</option>
                            <option value="sms">SMS (saved only)</option>
                        </select>
                    </label>
                    <button type="submit">Save notification</button>
                </form>
                <p id="notification-form-message" role="status"></p>
            </section>
        </div>
    );
}

export default Notifications;
