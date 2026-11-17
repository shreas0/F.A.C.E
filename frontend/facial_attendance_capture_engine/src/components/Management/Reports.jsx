import { Link } from "react-router-dom";
import { apiRequest, showMessage, showTable } from "../../services/faceApi";

function Reports() {
    async function getReport(event) {
        event.preventDefault();
        let studentId = event.target.elements.student_id.value;
        let startDate = event.target.elements.start_date.value;
        let endDate = event.target.elements.end_date.value;
        try {
            let result = await apiRequest(`/api/attendance/summary/${studentId}?start_date=${startDate}&end_date=${endDate}`);
            let rows = [
                ["Working days", result.working_days],
                ["Present", result.present],
                ["Late", result.late],
                ["Absent", result.absent],
                ["Attendance percentage", `${result.attendance_percentage}%`],
                ["Absent dates", result.absent_dates.join(", ") || "None"],
            ];
            showTable("report-table", ["Measure", "Result"], rows);
            showMessage("report-message", "Report loaded.");
        } catch (error) {
            showMessage("report-message", error.message);
        }
    }

    return (
        <div>
            <h1>Attendance Report</h1>
            <p><Link to="/Dashboard/Admin">Back to dashboard</Link></p>
            <form onSubmit={getReport}>
                <label>Student ID <input type="number" name="student_id" required /></label>
                <label>From <input type="date" name="start_date" required /></label>
                <label>To <input type="date" name="end_date" required /></label>
                <button type="submit">Create report</button>
            </form>
            <p id="report-message" role="status"></p>
            <div id="report-table"></div>
        </div>
    );
}

export default Reports;
