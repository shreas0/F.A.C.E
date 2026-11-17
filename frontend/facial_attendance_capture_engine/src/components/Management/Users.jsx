import { useEffect } from "react";
import { Link } from "react-router-dom";
import { apiRequest, showMessage, showTable } from "../../services/faceApi";

function Users() {
    async function loadUsers() {
        try {
            let result = await apiRequest("/api/users");
            let rows = [];
            for (let user of result.users) {
                rows.push([user.id, user.username, user.email, user.role, user.student_id, user.active ? "Active" : "Inactive"]);
            }
            showTable("users-table", ["ID", "Username", "Email", "Role", "Student ID", "Status"], rows);
            showMessage("users-message", `${rows.length} user(s) found.`);
        } catch (error) {
            showMessage("users-message", error.message);
        }
    }

    async function createUser(event) {
        event.preventDefault();
        let form = event.target;
        let studentId = form.elements.student_id.value;
        let data = {
            username: form.elements.username.value,
            email: form.elements.email.value,
            password: form.elements.password.value,
            role: form.elements.role.value,
            student_id: studentId ? Number(studentId) : null,
        };
        try {
            let result = await apiRequest("/api/users", { method: "POST", body: data });
            showMessage("user-form-message", result.message);
            form.reset();
            loadUsers();
        } catch (error) {
            showMessage("user-form-message", error.message);
        }
    }

    useEffect(function () {
        loadUsers();
    }, []);

    return (
        <div>
            <h1>Users and Roles</h1>
            <p><Link to="/Dashboard/Admin">Back to dashboard</Link></p>
            <section>
                <h2>Create an account</h2>
                <form onSubmit={createUser}>
                    <label>Username <input type="text" name="username" required /></label>
                    <label>Email <input type="email" name="email" required /></label>
                    <label>Password <input type="password" name="password" minLength="8" required /></label>
                    <label>Role
                        <select name="role">
                            <option value="student">Student</option>
                            <option value="reviewer">Reviewer</option>
                            <option value="admin">Admin</option>
                        </select>
                    </label>
                    <label>Student record ID (student account only) <input type="number" name="student_id" /></label>
                    <button type="submit">Create user</button>
                </form>
                <p id="user-form-message" role="status"></p>
            </section>
            <section>
                <h2>Account list</h2>
                <button type="button" onClick={loadUsers}>Refresh users</button>
                <p id="users-message" role="status"></p>
                <div id="users-table"></div>
            </section>
        </div>
    );
}

export default Users;
