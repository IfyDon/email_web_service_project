/**
 * Guards all dashboard routes.
 * Redirects to /login if not authenticated.
 * Shows a 2FA prompt if the user has authenticated but hasn't submitted their OTP.
 *
 * Place: frontend/src/components/auth/ProtectedRoute.jsx
 */

import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';

export default function ProtectedRoute() {
  const { isAuthenticated, requires2FA } = useAuthStore();
  const location = useLocation();

  // Mid-login 2FA challenge — only allow /login/2fa
  if (requires2FA && location.pathname !== '/login/2fa') {
    return <Navigate to="/login/2fa" replace />;
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{ from: location.pathname }}
        replace
      />
    );
  }

  return <Outlet />;
}