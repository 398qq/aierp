import axios from "axios";

const client = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

client.interceptors.request.use((config) => {
  // httpOnly cookie is sent automatically by browser — no JS access needed.
  // Explicitly read from cookie only when no Authorization header is set
  // (i.e., during SSR or when localStorage token is unavailable).
  if (!config.headers.Authorization) {
    // Token is in httpOnly cookie; axios sends it automatically via withCredentials
    // But we still support Bearer header for programmatic clients.
    const cookieToken = document.cookie
      .split("; ")
      .find((row) => row.startsWith("aierp_token="))
      ?.split("=")[1];
    if (cookieToken) {
      config.headers.Authorization = `Bearer ${cookieToken}`;
    }
  }
  return config;
});

client.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error.response?.status === 401) {
      // Clear any stale state and redirect to login
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default client;
