import apiClient from "./client";

export async function registerCustomer(payload) {
    const response = await apiClient.post("/customers/", payload);
    return response.data;
}
