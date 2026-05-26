/*
import { useLocation } from 'react-router-dom';
import { LogOut } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

const PAGE_TITLES = {
  '/dashboard':         'Overview',
  '/messages':          'Messages',
  '/domains':           'Sending Domains',
  '/templates':         'Email Templates',
  '/analytics':         'Analytics',
  '/webhooks':          'Webhooks',
  '/suppressions':      'Suppressions',
  '/settings/api-keys': 'API Keys',
  '/settings/account':  'Account Settings',
};

export default function TopBar() {
  const { pathname } = useLocation();
  const { logout, user } = useAuth();

  const title = PAGE_TITLES[pathname] ??
    Object.entries(PAGE_TITLES).find(([k]) => pathname.startsWith(k))?.[1] ??
    'MailFlow';

  return (
    <header className="flex h-16 flex-shrink-0 items-center justify-between
                       border-b border-gray-200 bg-white px-6">
      <h1 className="text-lg font-semibold text-gray-800">{title}</h1>

      <div className="flex items-center gap-4">
        {user && !user.is_verified && (
          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs
                           font-medium text-amber-700">
            Email unverified
          </span>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900"
        >
          <LogOut className="h-4 w-4" />
          Log out
        </button>
      </div>
    </header>
  );
}
*/