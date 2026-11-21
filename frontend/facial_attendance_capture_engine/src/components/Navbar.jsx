import { useNavigate, useLocation } from "react-router-dom";
import "./CSS/Navbar.css";

function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();

  const currentPath = location.pathname;

  return (
    <nav className="navbar">
      <div className="navbar-brand" onClick={() => navigate("/")} role="button" tabIndex={0}>
        <div className="brand-logo-mark">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 10h.01M15 10h.01M9.5 15a3.5 3.5 0 0 0 5 0" />
            <path d="M4 4v3M4 20v-3M20 4v3M20 20v-3M4 4h3M20 4h-3M4 20h3M20 20h-3" />
            <circle cx="12" cy="12" r="7" />
          </svg>
        </div>
        <span className="brand-name">F.A.C.E</span>
      </div>

      <div className="navbar-center-links">
        <button
          className={`nav-link-btn ${currentPath === "/" ? "active" : ""}`}
          onClick={() => navigate("/")}
        >
          Home
        </button>
        <button
          className={`nav-link-btn ${currentPath === "/About" || currentPath === "/about" ? "active" : ""}`}
          onClick={() => navigate("/About")}
        >
          About
        </button>
      </div>

      <div className="navbar-actions">
        <button
          className="navbar-signin-btn"
          onClick={() => navigate("/login")}
        >
          Sign In
        </button>
      </div>
    </nav>
  );
}

export default Navbar;
