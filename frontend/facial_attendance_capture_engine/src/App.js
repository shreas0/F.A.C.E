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
        <Route path= "Dashboard/Admin" element={<Admin />} />
        <Route path="Dashboard/Student" element={<Student />} />
        <Route path="StudentReg" element={<StudentReg />} />
        <Route path="ForgotPassword" element={<ForgotPassword />} />
        <Route path="Dashboard/Attendance" element={<Attendance />} />
        <Route path="Dashboard/Reports" element={<Reports />} />
        <Route path="Dashboard/Students" element={<Students />} />
        <Route path="Dashboard/Users" element={<Users />} />
        <Route path="Dashboard/Leaves" element={<Leaves />} />
        <Route path="Dashboard/Holidays" element={<Holidays />} />
        <Route path="Dashboard/Notifications" element={<Notifications />} />
       
      </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
