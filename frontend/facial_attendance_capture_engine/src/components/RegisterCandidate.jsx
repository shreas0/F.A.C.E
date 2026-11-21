import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "../services/faceApi";

function RegisterCandidate() {
    const [permissions, setPermissions] = useState({ current_role: "", allowed_posts: [] });
    const [fullName, setFullName] = useState("");
    const [userId, setUserId] = useState("");
    const [post, setPost] = useState("student");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("0000");
    const [className, setClassName] = useState("");
    const [linkedStudentId, setLinkedStudentId] = useState("");
    const [faceImage, setFaceImage] = useState(null);
    const [imagePreview, setImagePreview] = useState(null);
    const [statusMessage, setStatusMessage] = useState("");
    const [isSuccess, setIsSuccess] = useState(false);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        // Fetch permissions for the currently logged-in user
        apiRequest("/api/candidates/permissions")
            .then((data) => {
                setPermissions(data);
                if (data.allowed_posts && data.allowed_posts.length > 0) {
                    setPost(data.allowed_posts[0].post);
                }
            })
            .catch((err) => {
                setStatusMessage("Could not check permissions: " + err.message);
                setIsSuccess(false);
            });
    }, []);

    // Calculate auto-formatted username
    const cleanId = userId.trim();
    const effectiveUsername = cleanId
        ? cleanId.endsWith(`.${post}`)
            ? cleanId
            : `${cleanId}.${post}`
        : `[Candidate ID].${post}`;

    function handleImageChange(event) {
        const file = event.target.files[0];
        if (file) {
            setFaceImage(file);
            setImagePreview(URL.createObjectURL(file));
        } else {
            setFaceImage(null);
            setImagePreview(null);
        }
    }

    async function handleRegister(event) {
        event.preventDefault();
        setStatusMessage("");
        setLoading(true);

        const formData = new FormData();
        formData.append("full_name", fullName);
        formData.append("user_id", userId);
        formData.append("post", post);
        formData.append("email", email);
        formData.append("password", password || "0000");
        formData.append("class_name", className);
        formData.append("linked_student_id", linkedStudentId);

        if (faceImage && post === "student") {
            formData.append("face_image", faceImage);
        }

        try {
            const result = await apiRequest("/api/candidates/register", {
                method: "POST",
                body: formData,
            });

            setIsSuccess(true);
            setStatusMessage(result.message || "Candidate registered successfully!");

            // Reset form
            setFullName("");
            setUserId("");
            setEmail("");
            setPassword("0000");
            setClassName("");
            setLinkedStudentId("");
            setFaceImage(null);
            setImagePreview(null);
        } catch (error) {
            setIsSuccess(false);
            setStatusMessage(error.message || "Registration failed.");
        } finally {
            setLoading(false);
        }
    }

    const backUrl = permissions.current_role === "admin" ? "/Dashboard/Admin" : "/Dashboard/Staff";

    return (
        <div className="register-page">
            <h1>Register New Candidate</h1>
            <p>
                Register new candidates based on their post. The post is automatically appended to their User ID.
            </p>
            <p>
                <Link to={backUrl}>&larr; Back to Dashboard</Link>
            </p>

            <section>
                <form onSubmit={handleRegister}>
                    {/* Post / Role Selection */}
                    <label>
                        <span>Post / Role to Register</span>
                        <select
                            name="post"
                            value={post}
                            onChange={(e) => setPost(e.target.value)}
                            required
                        >
                            {permissions.allowed_posts.map((p) => (
                                <option key={p.post} value={p.post}>
                                    {p.label}
                                </option>
                            ))}
                        </select>
                        <small>
                            You are logged in as <strong>{permissions.current_role?.toUpperCase()}</strong>.
                        </small>
                    </label>

                    {/* Candidate ID */}
                    <label>
                        <span>Candidate ID / Number</span>
                        <input
                            type="text"
                            value={userId}
                            onChange={(e) => setUserId(e.target.value)}
                            placeholder="e.g. 2342 or 501"
                            required
                        />
                    </label>

                    {/* Auto-Username preview banner */}
                    <div className="username-preview">
                        Generated Sign-in ID: <strong>{effectiveUsername}</strong>
                        <small>
                            The candidate can sign in using ID <strong>{cleanId || "[Candidate ID]"}</strong> + Post <strong>{post}</strong>.
                        </small>
                    </div>

                    {/* Full Name */}
                    <label>
                        <span>Full Name</span>
                        <input
                            type="text"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            placeholder="e.g. Rahul Verma"
                            required
                        />
                    </label>

                    {/* Email */}
                    <label>
                        <span>Email (Optional)</span>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder={`Leave empty for default: ${effectiveUsername}@face.local`}
                        />
                    </label>

                    {/* Password */}
                    <label>
                        <span>Password (Default: 0000)</span>
                        <input
                            type="text"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="e.g. 0000"
                            required
                        />
                    </label>

                    {/* Role-Specific Fields */}
                    {post === "teacher" && (
                        <label>
                            <span>Assigned Class (Required for Teachers)</span>
                            <input
                                type="text"
                                value={className}
                                onChange={(e) => setClassName(e.target.value)}
                                placeholder="e.g. AD5E or 10A"
                                required
                            />
                        </label>
                    )}

                    {post === "student" && (
                        <>
                            <label>
                                <span>Class Name (Optional)</span>
                                <input
                                    type="text"
                                    value={className}
                                    onChange={(e) => setClassName(e.target.value)}
                                    placeholder="e.g. AD5E"
                                />
                            </label>

                            <label>
                                <span>Face Image for ESP Camera Attendance (Optional)</span>
                                <input
                                    type="file"
                                    accept="image/*"
                                    onChange={handleImageChange}
                                />
                                <small>
                                    Upload a clear frontal face image so the ESP32 camera recognizes the student.
                                </small>
                            </label>

                            {imagePreview && (
                                <div className="image-preview">
                                    <p style={{ margin: "0 0 6px 0", fontSize: "0.85rem" }}>Image Preview:</p>
                                    <img src={imagePreview} alt="Preview" />
                                </div>
                            )}
                        </>
                    )}

                    {post === "parent" && (
                        <label>
                            <span>Linked Student ID</span>
                            <input
                                type="number"
                                value={linkedStudentId}
                                onChange={(e) => setLinkedStudentId(e.target.value)}
                                placeholder="Enter student record ID"
                            />
                        </label>
                    )}

                    {/* Status Message */}
                    {statusMessage && (
                        <div className={`status-banner ${isSuccess ? "status-banner--success" : "status-banner--error"}`}>
                            {statusMessage}
                        </div>
                    )}

                    {/* Submit Button */}
                    <button type="submit" disabled={loading} className="login-btn">
                        {loading ? "Registering Candidate..." : `Register New ${post.toUpperCase()}`}
                    </button>
                </form>
            </section>
        </div>
    );
}

export default RegisterCandidate;
