const CART_KEY = "storefront_cart";

export function loadCart() {
    try {
        const raw = localStorage.getItem(CART_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

export function saveCart(items) {
    localStorage.setItem(CART_KEY, JSON.stringify(items));
}
