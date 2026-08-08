import axios from "axios";
import { ACCESS_TOKEN } from "./constants";

const apiUrl = "/api";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL : apiUrl,
});

// Endpoints a signed-out (or not-yet-verified) visitor must be able to call.
// A stale/expired access token sitting in localStorage must never be attached
// here — DRF's JWT auth rejects an invalid token before AllowAny is even
// checked, turning "log in" or "sign up" into a confusing 401.
const PUBLIC_PATHS = ["/token/", "/token/refresh/", "/register/", "/verify-otp/", "/resend-otp/"];

api.interceptors.request.use(
  (config) => {
    const isPublic = PUBLIC_PATHS.some((path) => config.url?.startsWith(path));
    const token = localStorage.getItem(ACCESS_TOKEN);
    if (token && !isPublic) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

export default api;
