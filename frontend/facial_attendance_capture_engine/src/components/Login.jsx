import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { singleSignIn } from "../services/adminAuth";
import "./CSS/Auth.css";

function Login() {
  const navigate = useNavigate();
  const [userId, setUserId] = useState("");
  const [post, setPost] = useState("student");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);

  // Dynamic preview calculation
  const cleanId = userId.trim();
  const effectiveUsername = cleanId
    ? cleanId.endsWith(`.${post}`)
      ? cleanId
      : `${cleanId}.${post}`
    : `[User ID].${post}`;

  // Quick fill test credentials
  function fillDemo() {
    setUserId("1234");
    setPassword("0000");
    setStatusMessage("");
  }

  async function handleLogin(event) {
    event.preventDefault();
    const enteredId = userId.trim();
    const enteredPost = post;
    const enteredPassword = password;

    if (!enteredId || !enteredPassword) {
      setStatusMessage("Please enter your User ID and Password.");
      setIsSuccess(false);
      return;
    }

    setIsLoading(true);
    setStatusMessage("");

    try {
      const result = await singleSignIn(enteredId, enteredPost, enteredPassword);
      setIsSuccess(true);
      setStatusMessage(result.message || "Sign-in successful!");

      const target =
        result.redirect ||
        (result.user?.role === "admin"
          ? "/Dashboard/Admin"
          : ["staff", "hod", "teacher", "reviewer"].includes(result.user?.role)
          ? "/Dashboard/Staff"
          : "/Dashboard/Student");

      setTimeout(() => {
        navigate(target);
      }, 300);
    } catch (error) {
      setIsSuccess(false);
      setStatusMessage(error.message || "Sign-in failed. Please verify your credentials.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card-centered">
        <div className="auth-header">
          <h1>Sign in to F.A.C.E</h1>
          <p>Unified portal for Students, Teachers, Staff, HODs, and Administrators.</p>
        </div>

        <form onSubmit={handleLogin} className="auth-form-clean">
          {/* Post / Role Selection */}
          <div className="form-group">
            <label htmlFor="auth-role">Post / Role</label>
            <select
              id="auth-role"
              className="form-input"
              value={post}
              onChange={(e) => setPost(e.target.value)}
              required
            >
              <option value="student">Student</option>
              <option value="staff">Staff Member</option>
              <option value="teacher">Teacher</option>
              <option value="hod">Head of Department (HOD)</option>
              <option value="reviewer">Leave Reviewer</option>
              <option value="parent">Parent / Guardian</option>
              <option value="admin">Administrator</option>
            </select>
          </div>

          {/* User ID / Roll Number */}
          <div className="form-group">
            <label htmlFor="auth-user-id">User ID / Roll Number</label>
            <input
              id="auth-user-id"
              className="form-input"
              type="text"
              name="user_id"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="e.g. 1234 or 2342"
              required
              autoFocus
            />
          </div>

          {/* Dynamic Username Preview */}
          <div className="unified-id-preview">
            <span>Signing in as:</span>
            <strong>{effectiveUsername}</strong>
          </div>

          {/* Password */}
          <div className="form-group">
            <label htmlFor="auth-password">Password</label>
            <div className="password-input-container">
              <input
                id="auth-password"
                className="form-input"
                type={showPassword ? "text" : "password"}
                name="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
              />
              <button
                type="button"
                className="password-toggle-text"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {/* Options: Remember & Forgot Password */}
          <div className="form-options-row">
            <label className="remember-checkbox">
              <input type="checkbox" name="remember" />
              <span>Keep me logged in</span>
            </label>
            <Link to="/ForgotPassword" className="forgot-password-link">
              Forgot password?
            </Link>
          </div>

          {/* Alert Message */}
          {statusMessage && (
            <div
              className={`auth-feedback-banner ${isSuccess ? "success" : "error"}`}
              role="alert"
            >
              {statusMessage}
            </div>
          )}

          {/* Submit Action */}
          <button
            type="submit"
            disabled={isLoading}
            className="auth-submit-button"
          >
            {isLoading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        {/* Test account helper */}
        <div className="auth-test-helper">
          <div>
            <span>Test Account: </span>
            <strong>1234 / 0000</strong>
          </div>
          <button type="button" onClick={fillDemo}>
            Fill
          </button>
        </div>
      </div>
    </div>
  );
}

export default Login;
