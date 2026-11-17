import { signInAdmin } from "../services/adminAuth";
import { useNavigate } from "react-router-dom";
import { showMessage } from "../services/faceApi";

function StaffSign() {
    const navigator= useNavigate();

    async function handleSubmit(event) {
        event.preventDefault();
        try {
            let username = event.target.elements.username.value;
            let password = event.target.elements.password.value;
            const admin = await signInAdmin(username, password);
            window.alert(`Welcome, admin ${admin.username}!`);
            navigator("/Dashboard/Admin");
        } catch (error) {
            showMessage("staff-login-message", error.message);
        }
    }

    return (
        <div className="main">
            <div className="sign-page">
                <form onSubmit={handleSubmit}>
                    <h1>Login</h1>
                    <p>Please enter your login details to sign in.</p>

                    <input type="text" name="username" placeholder="Enter Your Staff ID" required />

                    <input type="password" name="password" placeholder="Enter Password Here" required />

                    <div className="below-details">
                        <label>
                            <input type="checkbox" />
                            Keep me logged in
                        </label>

                        <a href="/ForgotPassword">Forgot password?</a>
                    </div>

                    <p id="staff-login-message" role="alert"></p>
                    <button type="submit">Log in</button>
                </form>
            </div>
        </div>
    );
}

export default StaffSign;
