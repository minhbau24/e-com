import axios from "axios";

const baseURL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").trim();

const apiClient = axios.create({
    baseURL,
    timeout: 10000,
});

apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem("jwt_token");
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export default apiClient;
