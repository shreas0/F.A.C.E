import { Link } from "react-router-dom";
import { apiRequest, showMessage } from "../../services/faceApi";

function ForgotPassword() {
    async function requestToken(event) {
        event.preventDefault();
        let email = event.target.elements.email.value;
        try {
            let result = await apiRequest("/api/password/forgot", { method: "POST", body: { email: email } });
            let message = result.message;
            if (result.development_token) {
                message += ` Development token: ${result.development_token}`;
            }
            showMessage("forgot-password-message", message);
        } catch (error) {
            showMessage("forgot-password-message", error.message);
        }
    }

    async function resetPassword(event) {
        event.preventDefault();
        let form = event.target;
        let token = form.elements.token.value;
        let newPassword = form.elements.new_password.value;
        try {
            let result = await apiRequest("/api/password/reset", {
                method: "POST",
                body: { token: token, new_password: newPassword },
            });
            showMessage("reset-password-message", result.message);
            form.reset();
        } catch (error) {
            showMessage("reset-password-message", error.message);
        }
    }

    return (
        <div>
            <h1>Password Reset</h1>
            <p><Link to="/StaffSign">Back to staff sign in</Link></p>
            <section>
                <h2>Request a reset token</h2>
                <form onSubmit={requestToken}>
                    <label>Email <input type="email" name="email" required /></label>
                    <button type="submit">Request token</button>
                </form>
                <p id="forgot-password-message" role="status"></p>
            </section>
            <section>
                <h2>Set a new password</h2>
                <form onSubmit={resetPassword}>
                    <label>Reset token <input type="text" name="token" required /></label>
                    <label>New password <input type="password" name="new_password" minLength="8" required /></label>
                    <button type="submit">Update password</button>
                </form>
                <p id="reset-password-message" role="status"></p>
            </section>
        </div>
    );
}

export default ForgotPassword;
