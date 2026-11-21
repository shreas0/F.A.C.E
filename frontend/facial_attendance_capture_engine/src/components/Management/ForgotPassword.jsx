import { Link } from "react-router-dom";
import { apiRequest, showMessage } from "../../services/faceApi";

function ForgotPassword() {
  async function requestToken(event) {
    event.preventDefault();
    let email = event.target.elements.email.value;
    try {
      let result = await apiRequest("/api/password/forgot", {
        method: "POST",
        body: { email: email },
      });
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
    <div className="auth-page">
      <div className="auth-card-centered" style={{ maxWidth: "500px" }}>
        <div className="auth-header">
          <h1>Password Reset</h1>
          <p>
            Request a password reset token with your registered email, or set a new password.
          </p>
          <p style={{ marginTop: "6px" }}>
            <Link to="/login" className="forgot-password-link">
              &larr; Back to Sign In
            </Link>
          </p>
        </div>

        {/* Section 1: Request Token */}
        <div style={{ marginBottom: "24px", paddingBottom: "24px", borderBottom: "1px solid var(--line)" }}>
          <h2 style={{ fontSize: "1.05rem", margin: "0 0 10px" }}>Request reset token</h2>
          <form onSubmit={requestToken} className="auth-form-clean">
            <div className="form-group">
              <label>Registered Email</label>
              <input
                className="form-input"
                type="email"
                name="email"
                placeholder="e.g. user@face.local"
                required
              />
            </div>
            <button type="submit" className="auth-submit-button" style={{ minHeight: "40px" }}>
              Request Token
            </button>
          </form>
          <p id="forgot-password-message" role="status" style={{ margin: "8px 0 0", fontWeight: "600" }}></p>
        </div>

        {/* Section 2: Set New Password */}
        <div>
          <h2 style={{ fontSize: "1.05rem", margin: "0 0 10px" }}>Set new password</h2>
          <form onSubmit={resetPassword} className="auth-form-clean">
            <div className="form-group">
              <label>Reset Token</label>
              <input
                className="form-input"
                type="text"
                name="token"
                placeholder="Paste your reset token"
                required
              />
            </div>
            <div className="form-group">
              <label>New Password (min 8 chars)</label>
              <input
                className="form-input"
                type="password"
                name="new_password"
                minLength="8"
                placeholder="Enter new password"
                required
              />
            </div>
            <button type="submit" className="auth-submit-button" style={{ minHeight: "40px" }}>
              Update Password
            </button>
          </form>
          <p id="reset-password-message" role="status" style={{ margin: "8px 0 0", fontWeight: "600" }}></p>
        </div>
      </div>
    </div>
  );
}

export default ForgotPassword;
