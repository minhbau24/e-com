import { Link } from "react-router-dom";
import { formatPrice } from "../../utils/currency";
import PromoCodeInput from "./PromoCodeInput";

function OrderSummary({
    subtotal,
    shipping,
    total,
    currentUser,
    loading,
    promoMessage,
    onApplyPromo,
    onCheckout,
}) {
    const shippingLabel = shipping === 0 ? "FREE" : formatPrice(shipping);

    return (
        <aside className="order-summary-card" aria-label="Order summary">
            <h3 className="summary-title">Order Summary</h3>

            <div className="summary-row">
                <span>Subtotal</span>
                <span>{formatPrice(subtotal)}</span>
            </div>
            <div className="summary-row">
                <span>Shipping</span>
                <span className={shipping === 0 ? "text-success fw-semibold" : ""}>{shippingLabel}</span>
            </div>
            <hr className="summary-divider" />
            <div className="summary-row summary-total">
                <span>Total</span>
                <span>{formatPrice(total)}</span>
            </div>

            <PromoCodeInput disabled={loading} onApply={onApplyPromo} />
            {promoMessage ? <div className="alert alert-info py-2 small mt-2 mb-0">{promoMessage}</div> : null}

            <div className="checkout-user mt-3">
                {currentUser ? (
                    <>
                        <p className="mb-1">
                            Checkout as: <strong>{currentUser.name || currentUser.email}</strong>
                        </p>
                        <Link to="/auth" className="summary-inline-link">
                            Change account
                        </Link>
                    </>
                ) : (
                    <>
                        <p className="mb-1">You are not logged in.</p>
                        <Link to="/auth" className="summary-inline-link">
                            Login to checkout
                        </Link>
                    </>
                )}
            </div>

            <button className="btn checkout-btn w-100" type="button" onClick={onCheckout} disabled={loading || !currentUser}>
                <span className="me-2" aria-hidden="true">PAY</span>
                {loading ? "Processing..." : "Thanh toán"}
            </button>
        </aside>
    );
}

export default OrderSummary;
