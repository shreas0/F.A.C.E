import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { apiRequest } from "../services/faceApi";

function ProtectedRoute({ allowedRoles, children }) {
  const [status, setStatus] = useState("checking");
  const [role, setRole] = useState("");

  useEffect(() => {
    let active = true;
    apiRequest("/api/me")
      .then((account) => {
        if (active) {
          setRole(account.role);
          setStatus("ready");
        }
      })
      .catch(() => {
        if (active) setStatus("signed_out");
      });
    return () => { active = false; };
  }, []);

  if (status === "checking") return <p role="status">Checking your account…</p>;
  if (status === "signed_out") return <Navigate to="/login" replace />;

  if (!allowedRoles.includes(role)) {
    const dashboard = role === "student" || role === "parent"
      ? "/Dashboard/Student"
      : role === "admin" ? "/Dashboard/Admin" : "/Dashboard/Staff";
    return <Navigate to={dashboard} replace />;
  }

  return children;
}

export default ProtectedRoute;
