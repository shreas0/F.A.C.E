import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest, showMessage, showTable } from "../../services/faceApi";

function Leaves() {
    const [role, setRole] = useState("");
    const canRequest = role === "student" || role === "parent";
    const canReview = ["admin", "hod", "teacher", "reviewer"].includes(role);
    async function loadLeaves() {
        try {
            let result = await apiRequest("/api/leaves");
            let rows = [];
            for (let item of result.leave_requests) {
                rows.push([item.id, item.student_id, item.name, item.start_date, item.end_date, item.reason, item.status, item.reviewer_note]);
            }
            showTable("leaves-table", ["Request", "Student ID", "Student", "From", "To", "Reason", "Status", "Review note"], rows);
            showMessage("leaves-message", `${rows.length} leave request(s) found.`);
        } catch (error) {
            showMessage("leaves-message", error.message);
        }
    }

    async function sendRequest(event) {
        event.preventDefault();
        let form = event.target;
        let data = {
            start_date: form.elements.start_date.value,
            end_date: form.elements.end_date.value,
            reason: form.elements.reason.value,
        };
        try {
            let result = await apiRequest("/api/leaves", { method: "POST", body: data });
            showMessage("leave-form-message", result.message);
            form.reset();
            loadLeaves();
        } catch (error) {
            showMessage("leave-form-message", error.message);
        }
    }

    async function reviewRequest(event) {
        event.preventDefault();
        let form = event.target;
        let requestId = form.elements.request_id.value;
        let data = { decision: form.elements.decision.value, note: form.elements.note.value };
        try {
            let result = await apiRequest(`/api/leaves/${requestId}/review`, { method: "POST", body: data });
            showMessage("leave-review-message", result.message);
            form.reset();
            loadLeaves();
        } catch (error) {
            showMessage("leave-review-message", error.message);
        }
    }

    useEffect(function () {
        apiRequest("/api/me").then((account) => setRole(account.role));
        loadLeaves();
    }, []);

    return (
        <div>
            <h1>Leave Requests</h1>
            <p><Link to="/Dashboard/Admin">Back to dashboard</Link></p>
            {canRequest && <section>
                <h2>Request leave</h2>
                <form onSubmit={sendRequest}>
                    <label>From <input type="date" name="start_date" required /></label>
                    <label>To <input type="date" name="end_date" required /></label>
                    <label>Reason <textarea name="reason" required /></label>
                    <button type="submit">Send request</button>
                </form>
                <p id="leave-form-message" role="status"></p>
            </section>}
            <section>
                <h2>Requests</h2>
                <button type="button" onClick={loadLeaves}>Refresh requests</button>
                <p id="leaves-message" role="status"></p>
                <div id="leaves-table"></div>
            </section>
            {canReview && <section>
                <h2>Review a request</h2>
                <form onSubmit={reviewRequest}>
                    <label>Request ID <input type="number" name="request_id" required /></label>
                    <label>Decision
                        <select name="decision">
                            <option value="approved">Approve</option>
                            <option value="rejected">Reject</option>
                        </select>
                    </label>
                    <label>Note <textarea name="note" /></label>
                    <button type="submit">Save decision</button>
                </form>
                <p id="leave-review-message" role="status"></p>
            </section>}
        </div>
    );
}

export default Leaves;
