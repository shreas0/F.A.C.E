import { Link } from "react-router-dom";

function About() {
  return (
    <article className="about-document">
      {/* Header */}
      <header className="about-header">
        <h1>About F.A.C.E.</h1>
        <p className="about-subtitle">Facial Attendance & Capture Engine</p>
      </header>

      {/* 1. Introduction */}
      <section className="about-section">
        <h2>1. Introduction</h2>
        <p>
          F.A.C.E. (Facial Attendance & Capture Engine) is an AI-powered biometric attendance management system developed to modernize the traditional attendance process through facial recognition and embedded computer vision technologies.
        </p>
        <p>
          Traditional attendance systems often rely on manual registers, identification cards, passwords, or fingerprint scanners. These methods can be time-consuming, inconvenient, and sometimes vulnerable to inaccuracies or proxy attendance.
        </p>
        <p>
          F.A.C.E. aims to address these limitations by introducing an automated, camera-based attendance solution that identifies registered individuals through their facial features and records their attendance digitally.
        </p>
        <p>
          The project combines embedded hardware, artificial intelligence, computer vision, backend development, database management, and frontend technologies into a unified system.
        </p>
        <p>
          Our primary objective is to make attendance management smarter, faster, more accessible, and less dependent on manual intervention.
        </p>
      </section>

      {/* 2. How the System Works */}
      <section className="about-section">
        <h2>2. How the System Works</h2>
        <p>
          F.A.C.E. follows a distributed architecture in which face detection, facial recognition, data processing, and attendance management work together.
        </p>
        <p>
          The process begins with an ESP32-CAM module equipped with an OV2640 camera. The device continuously captures low-resolution frames during its scheduled operating hours and performs local face detection using an optimized computer vision model.
        </p>
        <p>
          When a face is detected in consecutive frames, the system confirms its presence and captures a higher-resolution image. This image is then transmitted to the backend server for further processing.
        </p>
        <p>
          The backend handles facial recognition, compares the captured facial information against registered individuals, and determines the identity of the person.
        </p>
        <p>
          Once a successful identification is established, the backend communicates with the database to retrieve the individual's information and process the attendance entry.
        </p>
        <p>
          Finally, the frontend provides an interface through which administrators can access attendance records, view registered individuals, and interact with the attendance management system.
        </p>
      </section>

      {/* 3. Hardware Integration */}
      <section className="about-section">
        <h2>3. Hardware Integration</h2>
        <p>
          The hardware component of F.A.C.E. is built around the AI-Thinker ESP32-CAM development board, which integrates an ESP32 microcontroller with an OV2640 camera module.
        </p>
        <p>
          Instead of transmitting every captured frame to the server, the device performs initial face detection locally. This reduces unnecessary network communication and allows the system to transmit images only when a face has been successfully detected and confirmed.
        </p>
        <div className="about-highlight-box">
          <h3>Key hardware components:</h3>
          <ul>
            <li><strong>ESP32-CAM:</strong> Handles image acquisition, local processing, and communication with the backend.</li>
            <li><strong>OV2640 Camera:</strong> Captures image frames for face detection and subsequent recognition.</li>
            <li><strong>OLED Display:</strong> Provides visual feedback about the device's current status and operations.</li>
            <li><strong>Power Supply:</strong> Provides stable power to the embedded hardware.</li>
          </ul>
        </div>
        <p>
          The firmware is developed using ESP-IDF and ESP-WHO, with configurations designed to manage detection frequency, face confirmation, image quality, and retry intervals.
        </p>
      </section>

      {/* 4. Artificial Intelligence & Computer Vision */}
      <section className="about-section">
        <h2>4. Artificial Intelligence & Computer Vision</h2>
        <p>Computer vision is one of the core technologies behind F.A.C.E.</p>
        <p>The system uses a two-stage approach to facial processing:</p>
        <div className="about-two-stages">
          <div className="stage-card">
            <h3>Stage 1 – Face Detection</h3>
            <p>
              The ESP32-CAM performs local face detection to identify whether a human face is present in the camera's field of view. It checks consecutive frames to reduce false detections and unnecessary image transmissions.
            </p>
          </div>
          <div className="stage-card">
            <h3>Stage 2 – Facial Recognition</h3>
            <p>
              After successful detection, a high-resolution image is sent to the backend server, where facial recognition is performed to identify the registered individual. The system uses facial information to distinguish between registered users and unknown individuals.
            </p>
          </div>
        </div>
        <p>
          This separation of detection and recognition allows the embedded device to handle lightweight processing while delegating more computationally intensive operations to the backend.
        </p>
      </section>

      {/* 5. Backend Development */}
      <section className="about-section">
        <h2>5. Backend Development</h2>
        <p>
          The backend acts as the central processing layer of F.A.C.E.
        </p>
        <p>
          Developed using Python and Flask, it manages communication between the ESP32-CAM, facial recognition system, and database.
        </p>
        <p>Its responsibilities include:</p>
        <ul className="about-checklist">
          <li>Receiving captured images from the ESP32-CAM.</li>
          <li>Processing images for facial recognition.</li>
          <li>Matching detected individuals against registered users.</li>
          <li>Managing attendance-related operations.</li>
          <li>Communicating with the database.</li>
          <li>Providing API endpoints for frontend communication.</li>
          <li>Handling responses and system-level operations.</li>
        </ul>
        <p>
          The backend ensures that hardware operations, recognition processes, and attendance records remain properly coordinated.
        </p>
      </section>

      {/* 6. Database Management */}
      <section className="about-section">
        <h2>6. Database Management</h2>
        <p>
          The database layer is responsible for organizing and maintaining the information required by the system.
        </p>
        <p>
          It uses MySQL to store and manage structured data, including registered user information and attendance records.
        </p>
        <p>
          The database provides a centralized storage mechanism that allows the backend to retrieve user information, verify identification results, and maintain attendance history.
        </p>
        <p>Its primary responsibilities include:</p>
        <ul className="about-checklist">
          <li>Managing registered user records.</li>
          <li>Storing attendance entries.</li>
          <li>Maintaining relationships between users and their attendance records.</li>
          <li>Retrieving historical attendance information.</li>
          <li>Supporting efficient data access for the application.</li>
        </ul>
      </section>

      {/* 7. Frontend Development */}
      <section className="about-section">
        <h2>7. Frontend Development</h2>
        <p>
          The frontend serves as the primary interface between the system and its administrators.
        </p>
        <p>
          Developed using React.js, it provides a web-based environment for interacting with the attendance management system.
        </p>
        <p>
          The frontend communicates with the Flask backend through API requests, allowing information to be retrieved and displayed dynamically.
        </p>
        <p>Its functionality includes:</p>
        <ul className="about-checklist">
          <li>Displaying attendance information.</li>
          <li>Viewing registered individuals.</li>
          <li>Accessing attendance records.</li>
          <li>Presenting system information and responses.</li>
          <li>Providing an organized interface for attendance management.</li>
        </ul>
        <p>
          The frontend is designed to make the system accessible and easy to operate without requiring users to interact directly with the underlying hardware or backend processes.
        </p>
      </section>

      {/* 8. System Integration */}
      <section className="about-section">
        <h2>8. System Integration</h2>
        <p>
          One of the most important aspects of F.A.C.E. is the integration of multiple independent components into a single working solution.
        </p>
        <p>
          The ESP32-CAM communicates with the Flask backend to transfer captured images. The backend processes these images, interacts with the MySQL database, and provides the required information through APIs.
        </p>
        <p>
          The React frontend consumes these APIs and presents the resulting information through a user-friendly interface.
        </p>
        <p>
          This integration establishes a complete pipeline connecting embedded hardware, computer vision, backend processing, database operations, and frontend interaction.
        </p>
        <p>
          Each component performs a specific responsibility while contributing to the overall functionality of the system.
        </p>
      </section>

      {/* 9. Technologies Used */}
      <section className="about-section">
        <h2>9. Technologies Used</h2>
        <div className="tech-stack-grid">
          <div className="tech-category-card">
            <h3>Hardware & Embedded Systems</h3>
            <ul>
              <li>ESP32-CAM (AI-Thinker)</li>
              <li>OV2640 Camera Module</li>
              <li>OLED Display</li>
              <li>ESP-IDF</li>
              <li>ESP-WHO</li>
            </ul>
          </div>

          <div className="tech-category-card">
            <h3>Programming & Development</h3>
            <ul>
              <li>Python</li>
              <li>JavaScript</li>
              <li>C / C++</li>
            </ul>
          </div>

          <div className="tech-category-card">
            <h3>Artificial Intelligence & Computer Vision</h3>
            <ul>
              <li>OpenCV</li>
              <li>MediaPipe</li>
              <li>Facial Detection & Recognition</li>
            </ul>
          </div>

          <div className="tech-category-card">
            <h3>Backend</h3>
            <ul>
              <li>Flask</li>
              <li>Python REST APIs</li>
            </ul>
          </div>

          <div className="tech-category-card">
            <h3>Frontend</h3>
            <ul>
              <li>React.js</li>
              <li>HTML5 / CSS3</li>
              <li>JavaScript (ES6+)</li>
            </ul>
          </div>

          <div className="tech-category-card">
            <h3>Database</h3>
            <ul>
              <li>MySQL</li>
            </ul>
          </div>
        </div>
      </section>

      {/* 10. Project Team & Contributions */}
      <section className="about-section">
        <h2>10. Project Team & Contributions</h2>
        <p>
          F.A.C.E. is a collaborative project developed through the integration of different technical domains. Each team member is responsible for a major component of the system.
        </p>

        <div className="team-members-grid">
          <div className="team-card">
            <div className="team-role-tag">Frontend & Integration</div>
            <h3>Shreshtha Sharma</h3>
            <p>
              Responsible for developing the React.js frontend, designing the user interface, implementing frontend-backend communication, and integrating the different components of the system. Also contributes to the overall application structure and coordination between hardware, backend services, and frontend functionality.
            </p>
          </div>

          <div className="team-card">
            <div className="team-role-tag">Backend Development</div>
            <h3>Satwik Maurya</h3>
            <p>
              Responsible for developing the Python Flask backend, implementing server-side logic, handling image processing and facial recognition workflows, managing API communication, and coordinating backend operations.
            </p>
          </div>

          <div className="team-card">
            <div className="team-role-tag">Database Management</div>
            <h3>Vishal Verma</h3>
            <p>
              Responsible for designing and managing the MySQL database, organizing user information, maintaining attendance records, and implementing database operations required by the backend.
            </p>
          </div>
        </div>
      </section>

      {/* 11. Project Objective & Future Scope */}
      <section className="about-section">
        <h2>11. Project Objective & Future Scope</h2>
        <p>
          F.A.C.E. is designed to demonstrate how artificial intelligence and embedded systems can be combined to solve practical problems in attendance management.
        </p>
        <p>
          The project focuses on reducing manual effort, improving identification workflows, and providing a centralized platform for maintaining attendance records.
        </p>
        <p>Future improvements may include:</p>
        <ul className="about-checklist">
          <li>Advanced facial liveness detection to help prevent spoofing.</li>
          <li>Improved recognition accuracy under different lighting conditions.</li>
          <li>Real-time attendance analytics and reporting.</li>
          <li>Multi-device support for larger environments.</li>
          <li>Enhanced security and encrypted communication.</li>
          <li>Cloud-based deployment and remote administration.</li>
          <li>Automated notifications and attendance summaries.</li>
        </ul>
      </section>

      {/* Conclusion */}
      <section className="about-section about-conclusion">
        <h2>Conclusion</h2>
        <p>
          F.A.C.E. represents an integration of embedded systems, artificial intelligence, computer vision, and modern web development.
        </p>
        <p>
          By combining local face detection with server-side facial recognition and centralized attendance management, the project demonstrates a practical approach to automating an otherwise manual process.
        </p>
        <p>
          More than just an attendance application, F.A.C.E. is an exploration of how hardware and software technologies can work together to create intelligent, connected, and automated solutions.
        </p>

        <div className="motto-banner">
          F.A.C.E. &mdash; Recognize. Record. Simplify.
        </div>
      </section>

      <div className="about-footer-nav">
        <Link to="/login" className="home-action-btn primary">
          Go to Sign In Portal &rarr;
        </Link>
        <Link to="/" className="home-action-btn secondary">
          &larr; Back to Home
        </Link>
      </div>
    </article>
  );
}

export default About;
