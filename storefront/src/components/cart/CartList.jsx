import CartItem from "./CartItem";

function CartList({ items, updatingItemId, removingItemId, onDecrease, onIncrease, onRemove }) {
    return (
        <section className="cart-list-wrap">
            <header className="cart-list-head">
                <h2 className="cart-section-title">Your Cart</h2>
                <p className="cart-section-subtitle">Review your items before checkout</p>
            </header>

            <div className="cart-list">
                {items.map((item) => {
                    const key = `${item.id}-${item.productType || "product"}`;
                    const isBusy = updatingItemId === key || removingItemId === key;

                    return (
                        <CartItem
                            key={key}
                            item={item}
                            isBusy={isBusy}
                            isRemoving={removingItemId === key}
                            onDecrease={() => onDecrease(item)}
                            onIncrease={() => onIncrease(item)}
                            onRemove={() => onRemove(item)}
                        />
                    );
                })}
            </div>
        </section>
    );
}

export default CartList;
