import { useEffect } from "react";
import { Link } from "react-router-dom";
import { apiRequest, showMessage, showTable } from "../../services/faceApi";

function Attendance() {
    async function loadAttendance(event) {
        if (event) {
            event.preventDefault();
        }
        let form = document.getElementById("attendance-filter");
        let startDate = form.elements.start_date.value;
        let endDate = form.elements.end_date.value;
        let studentId = form.elements.student_id.value;
        let query = `start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`;
        if (studentId) {
            query += `&student_id=${encodeURIComponent(studentId)}`;
        }
        try {
            let result = await apiRequest(`/api/attendance?${query}`);
            let rows = [];
            for (let record of result.attendance) {
                rows.push([record.attendance_date, record.student_id, record.name, record.status, record.timestamp]);
            }
            showTable("attendance-table", ["Date", "Student ID", "Name", "Status", "Time"], rows);
            showMessage("attendance-message", `${rows.length} record(s) found.`);
        } catch (error) {
            showMessage("attendance-message", error.message);
        }
    }

    async function saveAttendance(event) {
        event.preventDefault();
        let form = event.target;
        let data = {
            student_id: form.elements.student_id.value,
            attendance_date: form.elements.attendance_date.value,
            status: form.elements.status.value,
        };
        try {
            let result = await apiRequest("/api/attendance/mark", { method: "POST", body: data });
            showMessage("manual-attendance-message", result.message);
            loadAttendance();
        } catch (error) {
            showMessage("manual-attendance-message", error.message);
        }
    }

    useEffect(function () {
        let endDate = new Date().toISOString().slice(0, 10);
        let start = document.getElementById("attendance-start-date");
        let end = document.getElementById("attendance-end-date");
        if (start && end) {
            start.value = endDate;
            end.value = endDate;
            loadAttendance();
        }
    }, []);

    function downloadPdf() {
        let form = document.getElementById("attendance-filter");
        let startDate = form.elements.start_date.value;
        let endDate = form.elements.end_date.value;
        let studentId = form.elements.student_id.value;
        let query = `start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`;
        if (studentId) {
            query += `&student_id=${encodeURIComponent(studentId)}`;
        }
        window.open(`http://localhost:5000/api/attendance/download-pdf?${query}`, "_blank");
    }

    return (
        <div>
            <h1>Attendance Records</h1>
            <p><Link to="/Dashboard/Admin">Back to dashboard</Link></p>
            <form id="attendance-filter" onSubmit={loadAttendance}>
                <label>From <input id="attendance-start-date" type="date" name="start_date" required /></label>
                <label>To <input id="attendance-end-date" type="date" name="end_date" required /></label>
                <label>Student ID (optional) <input type="number" name="student_id" /></label>
                <button type="submit">Search records</button>
                <button type="button" onClick={downloadPdf}>Download PDF</button>
            </form>
            <p id="attendance-message" role="status"></p>
            <div id="attendance-table"></div>
            <section>
                <h2>Set attendance for a student</h2>
                <form onSubmit={saveAttendance}>
                    <label>Student ID <input type="number" name="student_id" required /></label>
                    <label>Date <input type="date" name="attendance_date" required /></label>
                    <label>Status
                        <select name="status">
                            <option value="present">Present</option>
                            <option value="absent">Absent</option>
                            <option value="late">Late</option>
                            <option value="failed">Failed</option>
                        </select>
                    </label>
                    <button type="submit">Save attendance</button>
                </form>
                <p id="manual-attendance-message" role="status"></p>
            </section>
        </div>
    );
}

export default Attendance;
