import { useNavigate } from "react-router-dom";
import Pop from "./TestOption";
import "./CSS/Navbar.css";

function Navbar() {
  const navigate = useNavigate();

  function HandleCLick(target) {
    navigate(target);
  }

  function togglePop() {
    let pop = document.getElementById("test-options");
    pop.hidden = !pop.hidden;
  }

  return (
    <nav className="navbar">
      <div className="logo"></div>
        <div className="navbar-btns">
          <button onClick={() => HandleCLick("/")}>Home</button>
          <button onClick={() => HandleCLick("/about")}>About</button>
        </div>
  
      <div className="sign">
        <button onClick={togglePop}>Sign in</button>
        <div id="test-options" hidden>
          <Pop onClose={togglePop} />
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
