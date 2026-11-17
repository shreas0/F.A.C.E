import { useNavigate } from "react-router-dom";
import { signInStudent, signInStudentAccount } from "../services/adminAuth";
import { showMessage } from "../services/faceApi";

function StudentSign() {
    const navigate = useNavigate();

    async function handleIdLogin(event) {
        event.preventDefault();
        try {
            let studentId = event.target.elements.student_id.value;
            const student = await signInStudent(studentId);
            navigate("/Dashboard/Student", { state: { student } });
        } catch (loginError) {
            showMessage("student-login-message", loginError.message);
        }
    }

    async function handleAccountLogin(event) {
        event.preventDefault();
        try {
            let username = event.target.elements.username.value;
            let password = event.target.elements.password.value;
            const student = await signInStudentAccount(username, password);
            navigate("/Dashboard/Student", { state: { student } });
        } catch (loginError) {
            showMessage("student-login-message", loginError.message);
        }
    }

    return (
        <div className="main">
            <div className="sign-page">
                <form onSubmit={handleAccountLogin}>
                    <h1>Student Login</h1>
                    <p>Sign in with the username and password given by staff.</p>
                    <input type="text" name="username" placeholder="Username" required />
                    <input type="password" name="password" placeholder="Password" required />
                    <p id="student-login-message" role="alert"></p>
                    <button type="submit">Log in</button>
                </form>
                <form onSubmit={handleIdLogin}>
                    <h2>View-only sign in</h2>
                    <p>Use your numeric student ID to view your welcome page.</p>
                    <input type="text" name="student_id" inputMode="numeric" placeholder="Student ID" required />
                    <button type="submit">Continue</button>
                </form>
            </div>
        </div>
    );
}

export default StudentSign;
