import { useState } from "react";

function PromoCodeInput({ onApply, disabled }) {
    const [code, setCode] = useState("");

    const handleApply = (event) => {
        event.preventDefault();
        onApply(code.trim());
    };

    return (
        <form className="promo-form" onSubmit={handleApply}>
            <label className="promo-label" htmlFor="promo-code-input">
                Promo code
            </label>
            <div className="promo-row">
                <input
                    id="promo-code-input"
                    className="form-control"
                    type="text"
                    placeholder="Enter code"
                    value={code}
                    onChange={(event) => setCode(event.target.value.toUpperCase())}
                    disabled={disabled}
                />
                <button className="btn btn-outline-dark promo-btn" type="submit" disabled={disabled || !code.trim()}>
                    Apply
                </button>
            </div>
        </form>
    );
}

export default PromoCodeInput;
