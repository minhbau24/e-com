import apiClient from "./client";

export async function addToCart(payload) {
    const response = await apiClient.post("/cart/add/", payload);
    return response.data;
}

export async function getCartByCustomer(customerId) {
    const response = await apiClient.get(`/api/cart/carts/?customer_id=${customerId}`);
    const carts = Array.isArray(response.data) ? response.data : [];
    return carts[0] || null;
}

export async function updateCartQuantity(payload) {
    const response = await apiClient.put("/cart/update-quantity/", payload);
    return response.data;
}

export async function removeCartItem(payload) {
    const response = await apiClient.delete("/cart/remove-item/", { data: payload });
    return response.data;
}

export async function applyCoupon(payload) {
    const response = await apiClient.post("/cart/apply-coupon/", payload);
    return response.data;
}
