const API_URL = (process.env.REACT_APP_API_URL || "http://localhost:5000").replace(/\/$/, "");

async function postLogin(path, payload) {
    let response;
    try {
        response = await fetch(`${API_URL}${path}`, {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
    } catch {
        throw new Error("Could not reach the sign-in server. Make sure the backend is running and try again.");
    }

    let result;
    try {
        result = await response.json();
    } catch {
        throw new Error("The sign-in server returned an invalid response.");
    }
    if (!response.ok) throw new Error(result.message || "Could not sign in.");
    return result;
}

export async function signInAdmin(username, password) {
    const result = await postLogin("/api/admin/login", { username, password });
    return result.admin;
}

export async function signInStudentAccount(username, password) {
    const result = await postLogin("/api/student/account/login", { username, password });
    return result.student;
}

export async function singleSignIn(userId, post, password) {
    const result = await postLogin("/api/auth/single-login", {
        user_id: userId,
        post: post,
        password: password,
    });
    return result;
}
