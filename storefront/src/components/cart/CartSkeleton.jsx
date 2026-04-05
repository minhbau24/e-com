function CartSkeleton() {
    return (
        <div className="cart-skeleton-list" aria-hidden="true">
            {Array.from({ length: 3 }).map((_, index) => (
                <div className="cart-skeleton-item" key={index}>
                    <div className="cart-skeleton-thumb" />
                    <div className="cart-skeleton-content">
                        <div className="cart-skeleton-line short" />
                        <div className="cart-skeleton-line medium" />
                        <div className="cart-skeleton-line long" />
                    </div>
                </div>
            ))}
        </div>
    );
}

export default CartSkeleton;
