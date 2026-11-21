import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function Home() {
  const [data, setData] = useState({
    firstPara:
      "F.A.C.E is our team project: a face-recognition attendance system that replaces manual roll calls and proxy attendance. An ESP32-CAM captures a student's face at the entry point and sends it to our Flask server. The server matches it against enrolled students using facial landmark analysis and marks attendance in seconds. The result shows on a small OLED display at the device, so the student knows immediately whether they were marked.",
    secondPara:
      "Admins enroll students in person, which keeps identity verified from day one. Everyone starts the day as absent and turns present on a successful scan, and duplicate scans are ignored. The dashboard lets admins view the attendance log, search and filter it by date or student, and export it as CSV/Excel or PDF.",
  });

  useEffect(() => {
    fetch("/data.json")
      .then((res) => res.json())
      .then((result) => {
        if (result && result[0]) {
          setData({
            firstPara: result[0]["home-first-para"] || data.firstPara,
            secondPara: result[0]["home-second-para"] || data.secondPara,
          });
        }
      })
      .catch(() => {});
  }, []);

  return (
    <div className="home-wrapper">
      <div className="home-headline">
        <h1>Facial Attendance Capture Engine (F.A.C.E)</h1>
        <p className="home-tagline">Look at the camera. You're marked present.</p>
      </div>

      <div className="home-description-card">
        <p className="home-para">{data.firstPara}</p>
        <p className="home-para">{data.secondPara}</p>
        <div className="home-actions">
          <Link to="/login" className="home-action-btn primary">
            Sign In to Portal &rarr;
          </Link>
          <Link to="/About" className="home-action-btn secondary">
            About the Project
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Home;
