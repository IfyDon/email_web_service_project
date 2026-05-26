/**
 * Axios instance pre-configured for the MailFlow Django API.
 *
 * - Reads the API key from Zustand authStore on every request
 * - Attaches Authorization: Bearer <key> header automatically
 * - Intercepts 401 → clears auth state and redirects to /login
 * - Normalises error shape: every catch receives err.error.{code, message}
 *
 * Place: frontend/src/api/client.js
 */

import axios from 'axios';

// Base URL — empty string so Vite proxy handles /api/* in dev;
// set VITE_API_BASE_URL in .env for production direct-to-backend calls.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const client = axios.create({
  baseURL:        `${BASE_URL}/api/v1`,
  timeout:        15_000,
  headers: {
    'Content-Type': 'application/json',
    'Accept':       'application/json',
  },
  withCredentials: true,   // send session cookie for Django session auth fallback
});

// ── Request interceptor — attach API key ──────────────────────────────────────
client.interceptors.request.use(
  (config) => {
    // Lazy import to avoid circular dependency with the store
    const { getState } = require('@/store/authStore').useAuthStore;
    const { apiKey } = getState ? getState() : {};
    if (apiKey) {
      config.headers['Authorization'] = `Bearer ${apiKey}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ── Response interceptor — normalise errors + handle 401 ─────────────────────
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Import lazily to avoid circular deps
      import('@/store/authStore').then(({ useAuthStore }) => {
        useAuthStore.getState().clearAuth();
      });
      // Redirect to login preserving the current path
      const redirectTo = encodeURIComponent(window.location.pathname);
      window.location.href = `/login?next=${redirectTo}`;
    }

    // Normalise: ensure every error has err.error.{code, message}
    if (error.response?.data?.error) {
      return Promise.reject(error.response.data.error);
    }

    // Fallback for network errors, timeouts, etc.
    return Promise.reject({
      code:    'network_error',
      message: error.message || 'Network error. Please check your connection.',
    });
  },
);

export default client;

// ── Convenience helpers ───────────────────────────────────────────────────────

/** GET wrapper — returns response.data */
export const get = (url, params) =>
  client.get(url, { params }).then((r) => r.data);

/** POST wrapper */
export const post = (url, data) =>
  client.post(url, data).then((r) => r.data);

/** PATCH wrapper */
export const patch = (url, data) =>
  client.patch(url, data).then((r) => r.data);

/** PUT wrapper */
export const put = (url, data) =>
  client.put(url, data).then((r) => r.data);

/** DELETE wrapper */
export const del = (url) =>
  client.delete(url).then((r) => r.data);