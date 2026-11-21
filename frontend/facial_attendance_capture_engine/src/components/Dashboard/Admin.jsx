import { Link } from "react-router-dom";
import { useEffect } from "react";
import { apiRequest, showMessage } from "../../services/faceApi";

function Admin() {
    async function loadSession() {
        try {
            let result = await apiRequest("/api/attendance/session");
            if (result.active) {
                showMessage("session-status", `Session ${result.session_id} is active. Started: ${result.started_at}`);
            } else {
                showMessage("session-status", "No attendance session is active.");
            }
        } catch (error) {
            showMessage("session-status", error.message);
        }
    }

    async function startSession() {
        try {
            let result = await apiRequest("/api/attendance/session/start", { method: "POST" });
            showMessage("session-status", result.message);
        } catch (error) {
            showMessage("session-status", error.message);
        }
    }

    async function stopSession() {
        try {
            let result = await apiRequest("/api/attendance/session/stop", { method: "POST" });
            showMessage("session-status", result.message);
        } catch (error) {
            showMessage("session-status", error.message);
        }
    }

    async function signOut() {
        try {
            await apiRequest("/api/logout", { method: "POST" });
            window.location.href = "/StaffSign";
        } catch (error) {
            showMessage("admin-message", error.message);
        }
    }

    useEffect(function () {
        loadSession();
    }, []);

    return (
        <div>
            <h1>Attendance Management</h1>
            <p id="admin-message"></p>
            <section>
                <h2>Attendance Session</h2>
                <p id="session-status">Checking session...</p>
                <button type="button" onClick={loadSession}>Refresh status</button>
                <button type="button" onClick={startSession}>Start session</button>
                <button type="button" onClick={stopSession}>Stop session</button>
            </section>
            <nav aria-label="Attendance management pages">
                <ul>
                    <li><Link to="/RegisterCandidate">+ Register New Candidate (Any Role)</Link></li>
                    <li><Link to="/Dashboard/Attendance">Attendance records</Link></li>
                    <li><Link to="/Dashboard/Reports">Attendance report</Link></li>
                    <li><Link to="/Dashboard/Students">Student list</Link></li>
                    <li><Link to="/StudentReg">Register students and upload a CSV</Link></li>
                    <li><Link to="/Dashboard/Users">Users and roles</Link></li>
                    <li><Link to="/Dashboard/Leaves">Leave requests</Link></li>
                    <li><Link to="/Dashboard/Holidays">Holiday calendar</Link></li>
                    <li><Link to="/Dashboard/Notifications">Notifications</Link></li>
                </ul>
            </nav>
            <button type="button" onClick={signOut}>Sign out</button>
        </div>
    );
}

export default Admin;
