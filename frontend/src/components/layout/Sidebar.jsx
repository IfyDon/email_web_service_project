
import { NavLink } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  LayoutDashboard, Mail, Globe, FileText,
  BarChart2, Webhook, ShieldOff, Key, Settings,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

const NAV = [
  { to: '/dashboard',         label: 'Overview',     icon: LayoutDashboard },
  { to: '/messages',          label: 'Messages',     icon: Mail },
  { to: '/domains',           label: 'Domains',      icon: Globe },
  { to: '/templates',         label: 'Templates',    icon: FileText },
  { to: '/analytics',         label: 'Analytics',    icon: BarChart2 },
  { to: '/webhooks',          label: 'Webhooks',     icon: Webhook },
  { to: '/suppressions',      label: 'Suppressions', icon: ShieldOff },
];

const SETTINGS_NAV = [
  { to: '/settings/api-keys', label: 'API Keys', icon: Key },
  { to: '/settings/account',  label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  const { user, quotaPct, quotaUsed, quotaTotal, quotaExceeded } = useAuthStore();

  return (
    <aside
      className="flex w-64 flex-shrink-0 flex-col bg-gray-900 text-gray-100"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b border-gray-700 px-5">
        <span className="text-xl" aria-hidden="true">✉</span>
        <span className="text-lg font-bold tracking-tight text-white">MailFlow</span>
      </div>

      {/* Primary nav */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to} to={to} end={to === '/dashboard'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white',
              )
            }
          >
            <Icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
            {label}
          </NavLink>
        ))}

        <div className="my-3 border-t border-gray-700/50" />

        {SETTINGS_NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to} to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white',
              )
            }
          >
            <Icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Quota meter */}
      <div className="px-4 pb-3 text-xs">
        <div className="flex items-center justify-between text-gray-400 mb-1">
          <span>Quota</span>
          <span className={quotaExceeded ? 'text-red-400 font-medium' : ''}>
            {quotaUsed.toLocaleString()} / {quotaTotal.toLocaleString()}
          </span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-gray-700" role="progressbar"
             aria-valuenow={quotaPct} aria-valuemin={0} aria-valuemax={100}>
          <div
            className={clsx(
              'h-1.5 rounded-full transition-all duration-500',
              quotaExceeded   ? 'bg-red-500'
              : quotaPct > 75 ? 'bg-amber-400'
              :                 'bg-indigo-500',
            )}
            style={{ width: `${Math.min(100, quotaPct)}%` }}
          />
        </div>
      </div>

      {/* User */}
      <div className="border-t border-gray-700 px-4 py-3">
        <p className="truncate text-xs font-medium text-gray-200">
          {user?.full_name || user?.email}
        </p>
        <p className="truncate text-xs text-gray-500">{user?.role}</p>
      </div>
    </aside>
  );
}