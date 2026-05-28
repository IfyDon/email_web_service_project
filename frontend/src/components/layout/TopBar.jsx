/*
import { useLocation, Link } from 'react-router-dom';
import { LogOut, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/store/authStore';

const TITLES = {
  '/dashboard':'/messages':'/domains':'/templates':'/analytics':
  '/webhooks':'/suppressions':'/settings/api-keys':'/settings/account':
  // ← fill in as shown in the Layout artifact
};

export default function TopBar() {
  const { pathname } = useLocation();
  const { logout }   = useAuth();
  const { user, quotaExceeded } = useAuthStore();

  const title = Object.entries({
    '/dashboard':'Overview','/messages':'Messages','/domains':'Sending Domains',
    '/templates':'Email Templates','/analytics':'Analytics','/webhooks':'Webhooks',
    '/suppressions':'Suppressions','/settings/api-keys':'API Keys',
    '/settings/account':'Account Settings',
  }).find(([k]) => pathname === k || pathname.startsWith(k + '/'))?.[1] ?? 'MailFlow';

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-6">
      <h1 className="text-lg font-semibold text-gray-800">{title}</h1>
      <div className="flex items-center gap-4">
        {!user?.is_verified && (
          <span className="flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">
            <AlertTriangle className="h-3.5 w-3.5" />Email unverified
          </span>
        )}
        {quotaExceeded && (
          <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700">
            Quota exceeded
          </span>
        )}
        <button onClick={logout}
                className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 transition-colors">
          <LogOut className="h-4 w-4" /> Log out
        </button>
      </div>
    </header>
  );
}
*/