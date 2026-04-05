import { useState } from "react";
import { loginUser, registerUser } from "../api/auth";

function AuthPage({ onAuthSuccess }) {
    const [mode, setMode] = useState("login");
    const [form, setForm] = useState({ name: "", email: "", password: "", address: "" });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    const onSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setSuccess("");

        try {
            setLoading(true);
            if (mode === "register") {
                const data = await registerUser({
                    name: form.name,
                    email: form.email,
                    password: form.password,
                    address: form.address,
                });
                onAuthSuccess(data);
                setSuccess("Registered successfully.");
                return;
            }

            const data = await loginUser({
                email: form.email,
                password: form.password,
            });
            onAuthSuccess(data);
            setSuccess("Logged in successfully.");
        } catch (err) {
            setError(err.response?.data?.detail || err.message || "Authentication failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="row justify-content-center">
            <div className="col-md-8 col-lg-6">
                <div className="card shadow-sm">
                    <div className="card-body p-4">
                        <div className="d-flex gap-2 mb-3">
                            <button
                                type="button"
                                className={`btn btn-sm ${mode === "login" ? "btn-danger" : "btn-outline-secondary"}`}
                                onClick={() => setMode("login")}
                            >
                                Login
                            </button>
                            <button
                                type="button"
                                className={`btn btn-sm ${mode === "register" ? "btn-danger" : "btn-outline-secondary"}`}
                                onClick={() => setMode("register")}
                            >
                                Register
                            </button>
                        </div>

                        <h4 className="mb-3">{mode === "login" ? "Welcome back" : "Create account"}</h4>

                        <form onSubmit={onSubmit}>
                            {mode === "register" ? (
                                <>
                                    <label className="form-label">Name</label>
                                    <input
                                        className="form-control mb-3"
                                        required
                                        value={form.name}
                                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    />

                                    <label className="form-label">Address</label>
                                    <input
                                        className="form-control mb-3"
                                        value={form.address}
                                        onChange={(e) => setForm({ ...form, address: e.target.value })}
                                    />
                                </>
                            ) : null}

                            <label className="form-label">Email</label>
                            <input
                                type="email"
                                className="form-control mb-3"
                                required
                                value={form.email}
                                onChange={(e) => setForm({ ...form, email: e.target.value })}
                            />

                            <label className="form-label">Password</label>
                            <input
                                type="password"
                                className="form-control mb-3"
                                minLength={6}
                                required
                                value={form.password}
                                onChange={(e) => setForm({ ...form, password: e.target.value })}
                            />

                            <button className="btn btn-danger w-100" disabled={loading}>
                                {loading ? "Processing..." : mode === "login" ? "Login" : "Register"}
                            </button>
                        </form>

                        {error ? <div className="alert alert-danger mt-3 mb-0">{error}</div> : null}
                        {success ? <div className="alert alert-success mt-3 mb-0">{success}</div> : null}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default AuthPage;
