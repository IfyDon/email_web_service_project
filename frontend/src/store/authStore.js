/**
 * Global auth state — Zustand store.
 *
 * Persists user + apiKey to localStorage so sessions survive page refresh.
 * The Axios client reads apiKey from here on every request.
 *
 * Place: frontend/src/store/authStore.js
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

const _STORAGE_KEY = 'mf_auth';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      // ── State ──────────────────────────────────────────────────────────────
      user:          null,   // { id, email, full_name, role, is_verified, otp_enabled, … }
      apiKey:        null,   // raw Bearer token (ems_…)
      isAuthenticated: false,
      requires2FA:   false,  // set after login when server returns requires_2fa: true

      // ── Actions ────────────────────────────────────────────────────────────

      /** Called after successful login or signup. */
      setAuth: (user, apiKey = null) =>
        set({ user, apiKey, isAuthenticated: true, requires2FA: false }),

      /** Store the API key after it's been created in the dashboard. */
      setApiKey: (key) => set({ apiKey: key }),

      /** Update user profile fields without full re-login. */
      updateUser: (partial) =>
        set((s) => ({ user: { ...s.user, ...partial } })),

      /** Flag that 2FA code is required before full auth. */
      setPending2FA: () =>
        set({ requires2FA: true, isAuthenticated: false }),

      /** Clear everything — called on logout or 401. */
      clearAuth: () =>
        set({ user: null, apiKey: null, isAuthenticated: false, requires2FA: false }),

      // ── Selectors (stable references, memoised by Zustand) ────────────────
      get isVerified() { return get().user?.is_verified ?? false; },
      get has2FA()     { return get().user?.otp_enabled ?? false; },
      get quotaPct() {
        const u = get().user;
        if (!u || !u.monthly_quota) return 0;
        return Math.min(100, Math.round(u.emails_sent_mtd / u.monthly_quota * 100));
      },
    }),

    {
      name:    _STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      // Only persist these fields — don't store sensitive data beyond the key
      partialize: (state) => ({
        user:            state.user,
        apiKey:          state.apiKey,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);