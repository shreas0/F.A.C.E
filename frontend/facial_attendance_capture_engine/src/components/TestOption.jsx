import { useNavigate } from "react-router-dom";

function Pop({ onClose }) {
    const navigate = useNavigate();

    function HandleCLick(target) {
        navigate(target);
        onClose();
    }

    
    return (
        <div>
            <ul>
                <li>
                    <button onClick={() => HandleCLick("/StaffSign")}>
                        Staff
                    </button>
                </li>

                <li>
                    <button onClick={() => HandleCLick("/StudentSign")}>
                        Student
                    </button>
                </li>
            </ul>
        </div>
    );
}



export default Pop;
