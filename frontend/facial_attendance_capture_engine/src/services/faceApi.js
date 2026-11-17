const API_URL = (process.env.REACT_APP_API_URL || "http://localhost:5000").replace(/\/$/, "");

export async function apiRequest(path, options = {}) {
    let fetchOptions = {
        method: options.method || "GET",
        credentials: "include",
        headers: options.headers || {},
    };

    if (options.body !== undefined) {
        if (options.body instanceof FormData) {
            fetchOptions.body = options.body;
        } else {
            fetchOptions.headers["Content-Type"] = "application/json";
            fetchOptions.body = JSON.stringify(options.body);
        }
    }

    let response = await fetch(`${API_URL}${path}`, fetchOptions);
    let responseText = await response.text();
    let result = {};
    try {
        result = responseText ? JSON.parse(responseText) : {};
    } catch (error) {
        result = {};
    }
    if (!response.ok) {
        throw new Error(result.message || `The server returned an error (${response.status}).`);
    }
    return result;
}

export function showMessage(elementId, message) {
    let element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
    }
}

export function clearTable(elementId) {
    let element = document.getElementById(elementId);
    if (element) {
        element.textContent = "";
    }
    return element;
}

export function showTable(elementId, headings, rows) {
    let target = clearTable(elementId);
    if (!target) {
        return;
    }

    let table = document.createElement("table");
    let head = document.createElement("thead");
    let headRow = document.createElement("tr");
    for (let heading of headings) {
        let cell = document.createElement("th");
        cell.textContent = heading;
        headRow.appendChild(cell);
    }
    head.appendChild(headRow);
    table.appendChild(head);

    let body = document.createElement("tbody");
    for (let row of rows) {
        let tableRow = document.createElement("tr");
        for (let value of row) {
            let cell = document.createElement("td");
            cell.textContent = value === null || value === undefined ? "" : String(value);
            tableRow.appendChild(cell);
        }
        body.appendChild(tableRow);
    }
    table.appendChild(body);
    target.appendChild(table);
}
