import { useEffect } from "react";
import { Link } from "react-router-dom";
import { apiRequest, showMessage, showTable } from "../../services/faceApi";

function Students() {
    async function loadStudents() {
        try {
            let result = await apiRequest("/api/students");
            let rows = [];
            for (let student of result.students) {
                rows.push([student.id, student.student_number, student.name, student.email, student.class_name]);
            }
            showTable("students-table", ["ID", "Student Number", "Name", "Email", "Class"], rows);
            showMessage("students-message", `${rows.length} student(s) found.`);
        } catch (error) {
            showMessage("students-message", error.message);
        }
    }

    useEffect(function () {
        loadStudents();
    }, []);

    return (
        <div>
            <h1>Students</h1>
            <p><Link to="/Dashboard/Admin">Back to dashboard</Link></p>
            <button type="button" onClick={loadStudents}>Refresh students</button>
            <p id="students-message" role="status"></p>
            <div id="students-table"></div>
        </div>
    );
}

export default Students;
