import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';

export default function ProtectedRoute() {
  const { isAuthenticated, requires2FA } = useAuthStore();
  const location = useLocation();
  if (requires2FA && location.pathname !== '/login/2fa') return <Navigate to="/login/2fa" replace />;
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  return <Outlet />;
}
