import { Link, useLocation, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { apiRequest, showMessage } from "../../services/faceApi";

function Student() {
    const location = useLocation();
    const navigate = useNavigate();
    let student = location.state && location.state.student;

    async function loadSummary(event) {
        event.preventDefault();
        try {
            let startDate = event.target.elements.start_date.value;
            let endDate = event.target.elements.end_date.value;
            let account = await apiRequest("/api/me");
            let result = await apiRequest(`/api/attendance/summary/${account.student_id}?start_date=${startDate}&end_date=${endDate}`);
            showMessage("student-summary", `Attendance: ${result.attendance_percentage}% | Present: ${result.present} | Late: ${result.late} | Absent: ${result.absent} | Absent dates: ${result.absent_dates.join(", ") || "none"}`);
        } catch (error) {
            showMessage("student-summary", error.message);
        }
    }

    async function signOut() {
        await apiRequest("/api/logout", { method: "POST" });
        navigate("/StudentSign");
    }

    useEffect(function () {
        apiRequest("/api/me").then(function (account) {
            let welcomeStudent = student;
            if (!welcomeStudent) {
                welcomeStudent = { id: account.student_id, name: account.username };
            }
            showMessage("student-welcome", `Welcome, ${welcomeStudent.name}. Student ID: ${welcomeStudent.id}`);
        }).catch(function () {
            navigate("/StudentSign");
        });
    }, [navigate, student]);

    return (
        <div>
            <h1>Student and Family Dashboard</h1>
            <p id="student-welcome">Loading student...</p>
            <section>
                <h2>My Attendance</h2>
                <form onSubmit={loadSummary}>
                    <label>Start date <input type="date" name="start_date" required /></label>
                    <label>End date <input type="date" name="end_date" required /></label>
                    <button type="submit">Show attendance</button>
                </form>
                <p id="student-summary"></p>
            </section>
            <p><Link to="/Dashboard/Leaves">My leave requests</Link></p>
            <p><Link to="/Dashboard/Notifications">My notifications</Link></p>
            <button type="button" onClick={signOut}>Sign out</button>
        </div>
    );
}

export default Student;
