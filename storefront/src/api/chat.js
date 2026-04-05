import apiClient from "./client";

export async function sendChatMessage({ user_id, userId, query, debug = true }) {
    const response = await apiClient.post("/chat/", {
        user_id: user_id || userId || "anonymous",
        query,
        debug,
    });
    return response.data;
}
