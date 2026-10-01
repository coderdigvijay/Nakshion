import axios from "axios";

export const API_BASE_URL: string = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

function getToken(): string | null {
  try {
    return localStorage.getItem("token");
  } catch {
    return null;
  }
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    // Contract §1.4: 401 only means a missing/expired/revoked token.
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      try {
        localStorage.removeItem("token");
      } catch {
        // storage unavailable
      }
      if (!window.location.pathname.startsWith("/auth")) {
        window.location.href = "/auth?expired=1";
      }
    }
    return Promise.reject(error);
  },
);

export default api;
