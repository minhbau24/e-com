import apiClient from "./client";

export async function fetchReviewStats(productId) {
    const response = await apiClient.get(`/products/${productId}/reviews/stats/`);
    return response.data;
}

export async function fetchReviews(productId, { sort = "newest", page = 1, pageSize = 5 } = {}) {
    const response = await apiClient.get(`/products/${productId}/reviews/`, {
        params: {
            sort,
            page,
            page_size: pageSize,
        },
    });
    return response.data;
}

export async function submitReview(productId, payload) {
    const response = await apiClient.post(`/products/${productId}/reviews/`, payload);
    return response.data;
}
