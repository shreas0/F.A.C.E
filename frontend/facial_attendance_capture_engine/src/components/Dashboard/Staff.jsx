import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiRequest, showMessage } from "../../services/faceApi";

const roleNames = {
  hod: "Head of Department",
  teacher: "Teacher",
  staff: "Staff",
  reviewer: "Leave reviewer",
};

const rolePages = {
  hod: ["Register Candidate", "Attendance", "Reports", "Students", "Enrollment", "Leaves", "Holidays", "Notifications"],
  teacher: ["Attendance", "Reports", "Students", "Leaves"],
  staff: ["Register Candidate", "Attendance", "Reports", "Students", "Enrollment", "Leaves", "Notifications"],
  reviewer: ["Attendance", "Reports", "Leaves"],
};

const paths = {
  "Register Candidate": "/RegisterCandidate",
  Attendance: "/Dashboard/Attendance",
  Reports: "/Dashboard/Reports",
  Students: "/Dashboard/Students",
  Enrollment: "/StudentReg",
  Leaves: "/Dashboard/Leaves",
  Holidays: "/Dashboard/Holidays",
  Notifications: "/Dashboard/Notifications",
};

function StaffDashboard() {
  const navigate = useNavigate();
  const [account, setAccount] = useState(null);
  const canManageSession = account && ["hod", "staff"].includes(account.role);

  async function loadSession() {
    try {
      const result = await apiRequest("/api/attendance/session");
      showMessage("staff-session-status", result.active
        ? `Session ${result.session_id} is active.`
        : "No attendance session is active.");
    } catch (error) {
      showMessage("staff-session-status", error.message);
    }
  }

  async function updateSession(action) {
    try {
      const result = await apiRequest(`/api/attendance/session/${action}`, { method: "POST" });
      showMessage("staff-session-status", result.message);
    } catch (error) {
      showMessage("staff-session-status", error.message);
    }
  }

  async function signOut() {
    await apiRequest("/api/logout", { method: "POST" });
    navigate("/StaffSign");
  }

  useEffect(() => {
    apiRequest("/api/me").then((current) => {
      setAccount(current);
      if (["hod", "staff"].includes(current.role)) loadSession();
    }).catch(() => navigate("/StaffSign"));
  }, [navigate]);

  const pages = rolePages[account?.role] || [];

  return (
    <div>
      <h1>{roleNames[account?.role] || "Staff dashboard"}</h1>
      <p>Signed in as {account?.username || "…"}{account?.class_name ? ` · ${account.class_name}` : ""}</p>
      {canManageSession && (
        <section>
          <h2>Attendance session</h2>
          <p id="staff-session-status">Checking session…</p>
          <button type="button" onClick={loadSession}>Refresh status</button>
          <button type="button" onClick={() => updateSession("start")}>Start session</button>
          <button type="button" onClick={() => updateSession("stop")}>Stop session</button>
        </section>
      )}
      <nav aria-label="Work pages">
        <ul>
          {pages.map((page) => <li key={page}><Link to={paths[page]}>{page}</Link></li>)}
        </ul>
      </nav>
      <button type="button" onClick={signOut}>Sign out</button>
    </div>
  );
}

export default StaffDashboard;
