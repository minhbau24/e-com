import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { applyCoupon, getCartByCustomer } from "../api/cart";
import { createOrder } from "../api/orders";
import CartList from "../components/cart/CartList";
import OrderSummary from "../components/cart/OrderSummary";
import CartSkeleton from "../components/cart/CartSkeleton";

function CartPage({ cartItems, updateQty, removeItem, currentUser, onCheckoutSuccess }) {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [successMessage, setSuccessMessage] = useState("");
    const [updatingItemId, setUpdatingItemId] = useState("");
    const [removingItemId, setRemovingItemId] = useState("");
    const [promoMessage, setPromoMessage] = useState("");
    const [isPromoFreeShipping, setIsPromoFreeShipping] = useState(false);
    const [isCartLoading, setIsCartLoading] = useState(true);

    useEffect(() => {
        const timer = setTimeout(() => setIsCartLoading(false), 350);
        return () => clearTimeout(timer);
    }, []);

    const subtotal = cartItems.reduce((sum, item) => sum + Number(item.price || 0) * item.quantity, 0);
    const shipping = isPromoFreeShipping || subtotal > 300000 ? 0 : 30000;
    const total = subtotal + shipping;

    const getItemKey = (item) => `${item.id}-${item.productType || "product"}`;

    const handleDecrease = async (item) => {
        const key = getItemKey(item);
        try {
            setUpdatingItemId(key);
            await Promise.resolve(updateQty(item.id, item.quantity - 1));
        } finally {
            setUpdatingItemId("");
        }
    };

    const handleIncrease = async (item) => {
        const key = getItemKey(item);
        try {
            setUpdatingItemId(key);
            await Promise.resolve(updateQty(item.id, item.quantity + 1));
        } finally {
            setUpdatingItemId("");
        }
    };

    const handleRemove = async (item) => {
        const key = getItemKey(item);
        setRemovingItemId(key);
        setTimeout(async () => {
            try {
                await Promise.resolve(removeItem(item.id));
            } finally {
                setRemovingItemId("");
            }
        }, 220);
    };

    const handleApplyPromo = async (code) => {
        if (!code) {
            setIsPromoFreeShipping(false);
            setPromoMessage("Please enter a promo code");
            return;
        }

        if (currentUser?.id) {
            try {
                const couponResult = await applyCoupon({
                    customer_id: currentUser.id,
                    code,
                });
                const freeShipping = Boolean(couponResult?.free_shipping);
                setIsPromoFreeShipping(freeShipping);
                setPromoMessage(couponResult?.message || (freeShipping ? "Promo applied successfully" : "Promo applied"));
                return;
            } catch (couponError) {
                console.warn("Coupon API fallback", couponError?.response?.data || couponError.message);
            }
        }

        if (code === "FREESHIP") {
            setIsPromoFreeShipping(true);
            setPromoMessage("Promo applied: Free shipping on this order");
            return;
        }
        setIsPromoFreeShipping(false);
        setPromoMessage("Promo code is not valid or expired");
    };

    const handlePayment = async () => {
        if (!cartItems.length) {
            setError("Cart is empty");
            return;
        }

        if (!currentUser) {
            setError("Please log in to checkout");
            return;
        }

        try {
            setLoading(true);
            setError("");
            setSuccessMessage("");

            const cart = await getCartByCustomer(currentUser.id);
            if (!cart?.id) {
                setError("Cannot find cart for current user");
                return;
            }

            const orderPayload = {
                customer_id: currentUser.id,
                cart_id: cart.id,
                payment_method: "CREDIT_CARD",
                shipping_method: "STANDARD",
            };

            const order = await createOrder(orderPayload);

            setSuccessMessage(
                `Order #${order.order_id} created successfully!\n` +
                `Payment: ${order.payment_status}\n` +
                `Shipment: ${order.shipment_status}`
            );

            setTimeout(() => {
                onCheckoutSuccess?.();
                navigate("/");
            }, 2000);

        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || "Payment failed";
            setError(errorMsg);
            console.error("Order creation error:", err);
        } finally {
            setLoading(false);
        }
    };

    if (isCartLoading) {
        return <CartSkeleton />;
    }

    if (!cartItems.length) {
        return (
            <section className="cart-empty-state text-center py-5">
                <div className="cart-empty-icon" aria-hidden="true">CART</div>
                <h2 className="mb-2">Giỏ hàng trống</h2>
                <p className="text-muted mb-0">Bạn chưa có sản phẩm nào trong giỏ hàng.</p>
                <Link className="btn btn-dark mt-4 px-4 py-2" to="/">
                    Continue shopping
                </Link>
            </section>
        );
    }

    return (
        <div className="cart-page">
            <div className="cart-layout">
                <div className="cart-left">
                    <CartList
                        items={cartItems}
                        updatingItemId={updatingItemId}
                        removingItemId={removingItemId}
                        onDecrease={handleDecrease}
                        onIncrease={handleIncrease}
                        onRemove={handleRemove}
                    />
                </div>

                <div className="cart-right">
                    <div className="cart-summary-sticky">
                        <OrderSummary
                            subtotal={subtotal}
                            shipping={shipping}
                            total={total}
                            currentUser={currentUser}
                            loading={loading}
                            promoMessage={promoMessage}
                            onApplyPromo={handleApplyPromo}
                            onCheckout={handlePayment}
                        />
                    </div>
                </div>
            </div>

            {error && <div className="alert alert-danger small mt-3 mb-0">{error}</div>}
            {successMessage && <div className="alert alert-success small mt-3 mb-0" style={{ whiteSpace: "pre-line" }}>{successMessage}</div>}
        </div>
    );
}

export default CartPage;
