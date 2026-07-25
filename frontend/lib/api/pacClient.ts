/**
 * PAC — Axios HTTP Client
 *
 * Architecture:
 * - Access token is stored in memory (Zustand, never persisted to localStorage).
 * - Refresh token is stored in an httpOnly cookie, set by the Next.js BFF proxy.
 * - All API calls go through this client, which attaches the Bearer token.
 * - On 401: attempts a silent refresh via the BFF proxy.
 * - On refresh failure: clears the session and redirects to /login.
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";
import { API_BASE_URL } from "@/lib/utils/constants";
import { useSessionStore } from "@/lib/stores/useSessionStore";

// ── Backwards compatibility no-op ─────────────────────────────────────────────
export function initPacClientTokenStore(_store?: any) {}

// ── Client instance ───────────────────────────────────────────────────────────
export const pacClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120_000,
  headers: {

    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// ── Request interceptor — dynamically read live Bearer token ─────────────────
pacClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useSessionStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ── Response interceptor — handle 401, 403, normalise errors ─────────────────
let _isRefreshing = false;
let _refreshQueue: Array<{ resolve: (t: string) => void; reject: (e: unknown) => void }> = [];

pacClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // ── 401 Unauthorised → silent token refresh via Next.js BFF ────────────────
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (_isRefreshing) {
        return new Promise((resolve, reject) => {
          _refreshQueue.push({
            resolve: (token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              resolve(pacClient(originalRequest));
            },
            reject,
          });
        });
      }

      _isRefreshing = true;
      try {
        // Target Next.js BFF proxy endpoint explicitly (port 3000 origin)
        const refreshUrl = typeof window !== "undefined"
          ? `${window.location.origin}/api/auth/refresh`
          : "/api/auth/refresh";

        const res = await axios.post<{ access_token: string; user?: any }>(refreshUrl);
        const newToken = res.data.access_token;
        useSessionStore.getState().setAccessToken(newToken);
        if (res.data.user) {
          useSessionStore.getState().setUser(res.data.user);
        }

        // Flush queued requests
        _refreshQueue.forEach(({ resolve }) => resolve(newToken));
        _refreshQueue = [];

        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return pacClient(originalRequest);
      } catch {
        _refreshQueue.forEach(({ reject }) => reject(error));
        _refreshQueue = [];

        const currentToken = useSessionStore.getState().accessToken;
        if (!currentToken || !currentToken.startsWith("demo_token_")) {
          useSessionStore.getState().logout();
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
        }
      } finally {
        _isRefreshing = false;
      }
    }

    // ── 403 Forbidden ─────────────────────────────────────────────────────────
    if (error.response?.status === 403) {
      if (typeof window !== "undefined") {
        window.location.href = "/unauthorized";
      }
    }

    // ── Normalise error message ───────────────────────────────────────────────
    const data = error.response?.data as Record<string, unknown> | undefined;
    const message =
      (data?.detail as string) ??
      (data?.message as string) ??
      error.message ??
      "An unexpected error occurred";

    return Promise.reject(new Error(message));
  },
);
