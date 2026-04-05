import { useState } from "react";

function JwtTokenBar() {
    const [value, setValue] = useState(localStorage.getItem("jwt_token") || "");
    const [saved, setSaved] = useState(false);

    const save = () => {
        if (value.trim()) {
            localStorage.setItem("jwt_token", value.trim());
        } else {
            localStorage.removeItem("jwt_token");
        }
        setSaved(true);
        setTimeout(() => setSaved(false), 1200);
    };

    return (
        <div className="bg-light border-bottom py-2">
            <div className="container d-flex gap-2 align-items-center flex-wrap">
                <small className="text-muted">JWT (optional)</small>
                <input
                    className="form-control form-control-sm"
                    style={{ maxWidth: 420 }}
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    placeholder="Paste JWT token if your gateway requires auth"
                />
                <button className="btn btn-sm btn-outline-secondary" onClick={save}>
                    Save token
                </button>
                {saved ? <small className="text-success">Saved</small> : null}
            </div>
        </div>
    );
}

export default JwtTokenBar;
