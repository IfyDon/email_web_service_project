/**
 * Thin wrapper around the auth store + auth API calls.
 * Components import this instead of touching the store directly.
 *
 * Place: frontend/src/hooks/useAuth.js
 */

import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { authApi } from '@/api/auth';

export function useAuth() {
  const navigate  = useNavigate();
  const store     = useAuthStore();

  /** Sign up a new user and log them in automatically. */
  const signup = useCallback(async (data) => {
    const user = await authApi.signup(data);
    store.setAuth(user);
    navigate('/dashboard');
  }, [store, navigate]);

  /** Log in with email + password. Handles 2FA challenge. */
  const login = useCallback(async (data) => {
    const result = await authApi.login(data);
    if (result.requires_2fa) {
      store.setPending2FA();
      navigate('/login/2fa');
      return;
    }
    store.setAuth(result);
    navigate('/dashboard');
  }, [store, navigate]);

  /** Submit 2FA code after login challenge. */
  const submit2FA = useCallback(async (code) => {
    const user = await authApi.login2fa({ code });
    store.setAuth(user);
    navigate('/dashboard');
  }, [store, navigate]);

  /** Log out: clear store + call backend. */
  const logout = useCallback(async () => {
    try { await authApi.logout(); } catch { /* ignore */ }
    store.clearAuth();
    navigate('/login');
  }, [store, navigate]);

  /** Refresh the logged-in user's profile from the server. */
  const refreshUser = useCallback(async () => {
    const user = await authApi.me();
    store.updateUser(user);
    return user;
  }, [store]);

  return {
    user:            store.user,
    apiKey:          store.apiKey,
    isAuthenticated: store.isAuthenticated,
    requires2FA:     store.requires2FA,
    isVerified:      store.user?.is_verified ?? false,
    has2FA:          store.user?.otp_enabled ?? false,
    quotaPct:        store.quotaPct,
    signup,
    login,
    submit2FA,
    logout,
    refreshUser,
    setAuth:         store.setAuth,
    clearAuth:       store.clearAuth,
  };
}
