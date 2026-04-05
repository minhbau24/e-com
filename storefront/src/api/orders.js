import apiClient from "./client";

export async function createOrder(payload) {
    const response = await apiClient.post("/orders/", payload);
    return response.data;
}
