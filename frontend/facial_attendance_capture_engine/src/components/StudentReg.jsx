import { Link } from "react-router-dom";
import { apiRequest, showMessage } from "../services/faceApi";

function StudentReg() {
    async function uploadStudentCsv(event) {
        event.preventDefault();
        let form = event.target;
        let button = form.querySelector("button[type='submit']");
        let file = event.target.elements.file.files[0];
        if (!file) {
            showMessage("enrollment-message", "Choose a CSV file first.");
            return;
        }
        let formData = new FormData();
        formData.append("file", file);
        button.disabled = true;
        button.textContent = "Uploading...";
        try {
            let result = await apiRequest("/api/enrollment", { method: "POST", body: formData });
            let skipped = result.total_records - result.successful_records;
            showMessage("enrollment-message", `Batch ${result.batch_id}: ${result.successful_records} added; ${skipped} skipped or already enrolled.`);
        } catch (error) {
            showMessage("enrollment-message", error.message);
        } finally {
            button.disabled = false;
            button.textContent = "Upload student batch";
        }
    }

    async function uploadFaceImage(event) {
        event.preventDefault();
        let studentName = event.target.elements.student_name.value;
        let image = event.target.elements.image.files[0];
        if (!image) {
            showMessage("face-upload-message", "Choose an image first.");
            return;
        }
        let formData = new FormData();
        formData.append("student_name", studentName);
        formData.append("image", image);
        try {
            let result = await apiRequest("/api/students/register-face", { method: "POST", body: formData });
            showMessage("face-upload-message", result.message);
        } catch (error) {
            showMessage("face-upload-message", error.message);
        }
    }

    return (
        <div>
            <h1>Student Enrollment</h1>
            <p><Link to="/Dashboard/Admin">Back to dashboard</Link></p>
            <section>
                <h2>Upload a student CSV</h2>
                <p>CSV headings: student_number, name, email, class_name.</p>
                <form onSubmit={uploadStudentCsv}>
                    <label>CSV file <input type="file" name="file" accept=".csv,text/csv" required /></label>
                    <button type="submit">Upload student batch</button>
                </form>
                <p id="enrollment-message" role="status"></p>
            </section>
            <section>
                <h2>Add a face image</h2>
                <p>Add the student through the CSV first. The image watcher will save the face data after upload.</p>
                <form onSubmit={uploadFaceImage}>
                    <label>Student name <input type="text" name="student_name" required /></label>
                    <label>Face image <input type="file" name="image" accept="image/jpeg,image/png,image/webp,image/bmp" required /></label>
                    <button type="submit">Upload face image</button>
                </form>
                <p id="face-upload-message" role="status"></p>
            </section>
        </div>
    );
}

export default StudentReg;
