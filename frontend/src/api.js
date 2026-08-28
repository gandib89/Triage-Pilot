import axios from "axios";
import { getAccessToken, setAccessToken } from "./auth";

const apiUrl = "/api";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL : apiUrl,
  // The refresh token now lives in an httpOnly cookie, scoped by the
  // backend to the /api/token/ path — this just lets the browser attach
  // and accept it.
  withCredentials: true,
});

// Endpoints a signed-out (or not-yet-verified) visitor must be able to call.
// A stale/expired access token sitting in memory must never be attached
// here — DRF's JWT auth rejects an invalid token before AllowAny is even
// checked, turning "log in" or "sign up" into a confusing 401.
const PUBLIC_PATHS = ["/token/", "/token/refresh/", "/register/", "/verify-otp/", "/resend-otp/"];

const isPublicPath = (url) => PUBLIC_PATHS.some((path) => url?.startsWith(path));

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token && !isPublicPath(config.url)) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

async function postRefresh() {
  const res = await api.post("/token/refresh/");
  setAccessToken(res.data.access);
  return res.data.access;
}

// A page reload wipes the in-memory access token, so on first use after a
// reload it's normal to have none yet — this refreshes it from the cookie.
// Concurrent 401s share one in-flight refresh instead of racing the backend.
//
// The refresh cookie is shared across every tab, but each tab's in-memory
// access token isn't — so two tabs opened at once can both read the same
// (still valid) cookie and both call /token/refresh/ before either response
// lands. The backend only allows one-shot use of a refresh token, and the
// second call would then look identical to a stolen-token replay, tripping
// family-wide revocation and logging every tab out. navigator.locks
// serializes the actual network call across tabs so that never happens: by
// the time a second tab gets its turn, the cookie has already rotated.
let refreshPromise = null;

export function refreshAccessToken() {
  if (!refreshPromise) {
    const run = navigator.locks
      ? () => navigator.locks.request("triagepilot-token-refresh", postRefresh)
      : postRefresh;
    refreshPromise = run()
      .catch((err) => {
        setAccessToken(null);
        throw err;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    if (response?.status === 401 && config && !isPublicPath(config.url) && !config._retried) {
      config._retried = true;
      try {
        const access = await refreshAccessToken();
        config.headers.Authorization = `Bearer ${access}`;
        return api(config);
      } catch {
        // Refresh failed too — fall through and reject with the original 401.
      }
    }
    return Promise.reject(error);
  },
);

export default api;
