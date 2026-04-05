import { Link } from "react-router-dom";
import { formatPrice } from "../../utils/currency";

function CartItem({ item, isBusy, isRemoving, onDecrease, onIncrease, onRemove }) {
    const image = item.image || item.image_url || item.thumbnail || "https://placehold.co/120x120?text=Item";

    return (
        <article className={`cart-item-card ${isRemoving ? "is-removing" : ""}`}>
            <img className="cart-item-thumb" src={image} alt={item.title || "Product"} loading="lazy" />

            <div className="cart-item-main">
                <Link className="cart-item-title" to={`/products/${item.id}`}>
                    {item.title}
                </Link>
                <p className="cart-item-price">{formatPrice(item.price)}</p>

                <div className="cart-item-actions">
                    <div className="qty-control" role="group" aria-label="Update quantity">
                        <button className="btn qty-btn" type="button" onClick={onDecrease} disabled={isBusy || item.quantity <= 1}>
                            -
                        </button>
                        <span className="qty-value">{item.quantity}</span>
                        <button className="btn qty-btn" type="button" onClick={onIncrease} disabled={isBusy}>
                            +
                        </button>
                    </div>

                    <button className="btn btn-link text-danger cart-remove-btn" type="button" onClick={onRemove} disabled={isBusy}>
                        <span className="trash-icon" aria-hidden="true">
                            DEL
                        </span>
                        Remove
                    </button>
                </div>
            </div>

            <div className="cart-item-total">{formatPrice(Number(item.price || 0) * Number(item.quantity || 0))}</div>
        </article>
    );
}

export default CartItem;
