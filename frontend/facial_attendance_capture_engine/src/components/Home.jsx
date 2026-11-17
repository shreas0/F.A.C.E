import { useEffect } from "react";

function Home() {
  useEffect(() => {
    fetch("/data.json")
      .then((response) => response.json())
      .then((result) => {
        let firstParagraph = document.getElementById("home-first-para");
        let secondParagraph = document.getElementById("home-second-para");
        if (firstParagraph && result[0]) {
          firstParagraph.textContent = result[0]["home-first-para"];
        }
        if (secondParagraph && result[0]) {
          secondParagraph.textContent = result[0]["home-second-para"];
        }
      });
  }, []);

  return (
    <div style={{ padding: "40px", color: "black" }}>
      <div className="home-headline">
        <h1>Facial Attendance Capture Engine (F.A.C.E)</h1>
        <p>Look at the camera. You're marked present.</p>
      </div>

      <div className="home-description">
        <p id="home-first-para"></p>
        <p id="home-second-para"></p>
      </div>
    </div>
  );
}

export default Home;
