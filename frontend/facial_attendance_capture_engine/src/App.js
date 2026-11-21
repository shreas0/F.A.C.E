import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./components/Home";
import Login from "./components/Login";
import RootLayout from "./components/RootLayout";
import About from "./components/About";
import StaffSign from "./components/StaffSign";
import StudentSign from "./components/StudentSign";
import Admin from "./components/Dashboard/Admin";
import Student from "./components/Dashboard/Student";
import StudentReg from "./components/StudentReg";
import Attendance from "./components/Management/Attendance";
import Reports from "./components/Management/Reports";
import Students from "./components/Management/Students";
import Users from "./components/Management/Users";
import Leaves from "./components/Management/Leaves";
import Holidays from "./components/Management/Holidays";
import Notifications from "./components/Management/Notifications";
import ForgotPassword from "./components/Management/ForgotPassword";
import ProtectedRoute from "./components/ProtectedRoute";
import StaffDashboard from "./components/Dashboard/Staff";
import RegisterCandidate from "./components/RegisterCandidate";



function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RootLayout />}>
        <Route index element={<Home />} />
        <Route path="login" element={<Login />} />
        <Route path="StaffSign" element={<StaffSign />} />
        <Route path="StudentSign" element={<StudentSign />} />
        <Route path="About" element={<About />} />
        <Route path="Dashboard/Admin" element={<ProtectedRoute allowedRoles={["admin"]}><Admin /></ProtectedRoute>} />
        <Route path="Dashboard/Staff" element={<ProtectedRoute allowedRoles={["hod", "teacher", "staff", "reviewer"]}><StaffDashboard /></ProtectedRoute>} />
        <Route path="Dashboard/Student" element={<ProtectedRoute allowedRoles={["student", "parent"]}><Student /></ProtectedRoute>} />
        <Route path="StudentReg" element={<ProtectedRoute allowedRoles={["admin", "hod", "staff"]}><StudentReg /></ProtectedRoute>} />
        <Route path="RegisterCandidate" element={<ProtectedRoute allowedRoles={["admin", "hod", "staff"]}><RegisterCandidate /></ProtectedRoute>} />
        <Route path="ForgotPassword" element={<ForgotPassword />} />
        <Route path="Dashboard/Attendance" element={<ProtectedRoute allowedRoles={["admin", "hod", "staff", "teacher", "reviewer"]}><Attendance /></ProtectedRoute>} />
        <Route path="Dashboard/Reports" element={<ProtectedRoute allowedRoles={["admin", "hod", "staff", "teacher", "reviewer", "student", "parent"]}><Reports /></ProtectedRoute>} />
        <Route path="Dashboard/Students" element={<ProtectedRoute allowedRoles={["admin", "hod", "staff", "teacher", "reviewer"]}><Students /></ProtectedRoute>} />
        <Route path="Dashboard/Users" element={<ProtectedRoute allowedRoles={["admin"]}><Users /></ProtectedRoute>} />
        <Route path="Dashboard/Leaves" element={<ProtectedRoute allowedRoles={["admin", "hod", "staff", "teacher", "reviewer", "student"]}><Leaves /></ProtectedRoute>} />
        <Route path="Dashboard/Holidays" element={<ProtectedRoute allowedRoles={["admin", "hod", "staff", "teacher", "reviewer", "student", "parent"]}><Holidays /></ProtectedRoute>} />
        <Route path="Dashboard/Notifications" element={<ProtectedRoute allowedRoles={["admin", "hod", "staff", "teacher", "reviewer", "student", "parent"]}><Notifications /></ProtectedRoute>} />
       
      </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
