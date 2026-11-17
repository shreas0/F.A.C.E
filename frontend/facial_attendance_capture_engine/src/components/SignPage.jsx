function SignPage() {
    return (
        <div className="main">
            <div className="sign-page">
                <form>
                    <h1>Login</h1>
                    <p>Please enter your login details to sign in.</p>

                    <input
                        type="number"
                        placeholder="Enter Your Enrollment Id.."
                    />

                    <input
                        type="password"
                        placeholder="Enter Password Here.."
                    />

                    <div className="below-details">
                        <label>
                            <input type="checkbox" />
                            Keep me logged in
                        </label>

                        <a href="">Forgot password?</a>
                    </div>

                    <button type="submit">Log in</button>
                </form>
            </div>
        </div>
    );
}

export default SignPage;