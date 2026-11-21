import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest, showMessage, showTable } from "../../services/faceApi";

function Holidays() {
    const [role, setRole] = useState("");
    const canManage = role === "admin" || role === "hod";
    async function loadHolidays() {
        let yearInput = document.getElementById("holiday-year");
        let year = yearInput.value || new Date().getFullYear();
        try {
            let result = await apiRequest(`/api/holidays?start_date=${year}-01-01&end_date=${year}-12-31`);
            let rows = [];
            for (let holiday of result.holidays) {
                rows.push([holiday.holiday_date, holiday.name]);
            }
            showTable("holidays-table", ["Date", "Holiday"], rows);
            showMessage("holidays-message", `${rows.length} holiday(s) found.`);
        } catch (error) {
            showMessage("holidays-message", error.message);
        }
    }

    async function addHoliday(event) {
        event.preventDefault();
        let form = event.target;
        let data = { holiday_date: form.elements.holiday_date.value, name: form.elements.name.value };
        try {
            let result = await apiRequest("/api/holidays", { method: "POST", body: data });
            showMessage("holiday-form-message", result.message);
            form.reset();
            loadHolidays();
        } catch (error) {
            showMessage("holiday-form-message", error.message);
        }
    }

    useEffect(function () {
        let yearInput = document.getElementById("holiday-year");
        yearInput.value = new Date().getFullYear();
        apiRequest("/api/me").then((account) => setRole(account.role));
        loadHolidays();
    }, []);

    return (
        <div>
            <h1>Holiday Calendar</h1>
            <p><Link to="/Dashboard/Admin">Back to dashboard</Link></p>
            {canManage && <section>
                <h2>Add holiday</h2>
                <form onSubmit={addHoliday}>
                    <label>Date <input type="date" name="holiday_date" required /></label>
                    <label>Name <input type="text" name="name" required /></label>
                    <button type="submit">Add holiday</button>
                </form>
                <p id="holiday-form-message" role="status"></p>
            </section>}
            <section>
                <h2>Calendar list</h2>
                <label>Year <input type="number" id="holiday-year" /></label>
                <button type="button" onClick={loadHolidays}>Show year</button>
                <p id="holidays-message" role="status"></p>
                <div id="holidays-table"></div>
            </section>
        </div>
    );
}

export default Holidays;
