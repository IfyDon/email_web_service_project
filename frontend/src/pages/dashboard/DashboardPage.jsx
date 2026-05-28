/**
 * Dashboard overview — 7-day stats, activity chart, recent messages.
 *
 * Security:
 *  - All API values sanitised in useStats / useApi hooks
 *  - Message subjects truncated and escaped by React (no dangerouslySetInnerHTML)
 *  - Dates formatted with date-fns (no eval-based parsing)
 *  - Error states show generic messages only
 *
 * Place: frontend/src/pages/dashboard/DashboardPage.jsx
 */

import { useEffect }     from 'react';
import { Link }          from 'react-router-dom';
import { format, parseISO, isValid } from 'date-fns';
import { RefreshCw, ArrowRight, TrendingUp, TrendingDown } from 'lucide-react';
import { useStats }      from '@/hooks/useStats';
import { useApi }        from '@/hooks/useApi';
import { messagesApi }   from '@/api/messages';
import StatCard          from '@/components/charts/StatCard';
import ActivityChart     from '@/components/charts/ActivityChart';

// ── Helpers ───────────────────────────────────────────────────────────────────

function safeDate(str) {
  try {
    const d = parseISO(str);
    return isValid(d) ? format(d, 'MMM d, HH:mm') : '—';
  } catch { return '—'; }
}

const STATUS_BADGE = {
  queued:    { label: 'Queued',     cls: 'badge-yellow' },
  sending:   { label: 'Sending',    cls: 'badge-yellow' },
  delivered: { label: 'Delivered',  cls: 'badge-green'  },
  opened:    { label: 'Opened',     cls: 'badge-green'  },
  clicked:   { label: 'Clicked',    cls: 'badge-indigo' },
  bounced:   { label: 'Bounced',    cls: 'badge-red'    },
  complained:{ label: 'Complained', cls: 'badge-orange' },
  failed:    { label: 'Failed',     cls: 'badge-red'    },
};

const COUNT_CARDS = [
  { key: 'sent',       label: 'Sent',       icon: '📤', status: 'default' },
  { key: 'delivered',  label: 'Delivered',  icon: '✅', status: 'success' },
  { key: 'opened',     label: 'Opened',     icon: '👁',  status: 'info'    },
  { key: 'clicked',    label: 'Clicked',    icon: '🖱',  status: 'info'    },
  { key: 'bounced',    label: 'Bounced',    icon: '⚠️',  status: 'warning' },
  { key: 'complained', label: 'Complained', icon: '🚩',  status: 'danger'  },
];

// ── Mini rate badge ───────────────────────────────────────────────────────────
function RateCard({ label, value, loading }) {
  const n = Number.isFinite(Number(value)) && Number(value) >= 0
    ? Number(value).toFixed(1)
    : '0.0';

  return (
    <div className="card p-4 flex items-center justify-between">
      {loading ? (
        <div className="h-4 w-32 bg-gray-100 rounded animate-pulse" />
      ) : (
        <>
          <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">{label}</p>
          <p className="text-lg font-bold text-gray-800 tabular-nums">{n}%</p>
        </>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const {
    summary, timeline,
    loading: statsLoading,
    error:   statsError,
    refetch,
  } = useStats({ days: 7, granularity: 'daily' });

  const {
    data:    msgData,
    loading: msgsLoading,
    error:   msgsError,
    execute: loadMessages,
  } = useApi(() => messagesApi.list({ page: 1, page_size: 10 }), {
    initialData: null,
  });

  useEffect(() => { loadMessages(); }, []);

  const messages = Array.isArray(msgData?.results) ? msgData.results : [];

  return (
    <div className="space-y-6 max-w-7xl">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Last 7 days</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Your sending activity at a glance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/analytics"
                className="btn-secondary text-xs px-3 py-1.5 gap-1.5">
            Full analytics <ArrowRight className="h-3.5 w-3.5" />
          </Link>
          <button
            onClick={refetch}
            disabled={statsLoading}
            aria-label="Refresh stats"
            className="btn-secondary text-xs px-3 py-1.5 gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${statsLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* ── Stats error ───────────────────────────────────────────────────── */}
      {statsError && !statsLoading && (
        <div role="alert"
             className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 animate-fade-in">
          Failed to load statistics.{' '}
          <button onClick={refetch} className="underline font-medium">Retry</button>
        </div>
      )}

      {/* ── Count cards ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
        {COUNT_CARDS.map(({ key, label, icon, status }) => (
          <StatCard
            key={key}
            label={label}
            value={summary[key]}
            icon={icon}
            status={status}
            loading={statsLoading}
          />
        ))}
      </div>

      {/* ── Rate row ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <RateCard label="Open rate"      value={summary.open_rate}      loading={statsLoading} />
        <RateCard label="Click rate"     value={summary.click_rate}     loading={statsLoading} />
        <RateCard label="Bounce rate"    value={summary.bounce_rate}    loading={statsLoading} />
        <RateCard label="Complaint rate" value={summary.complaint_rate} loading={statsLoading} />
      </div>

      {/* ── Activity chart ────────────────────────────────────────────────── */}
      <div className="card p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-1">
          Sending activity — last 7 days
        </h3>
        <p className="text-xs text-gray-400 mb-4">
          Opens and clicks may lag by a few minutes after delivery.
        </p>
        <ActivityChart
          data={timeline}
          series={['sent', 'delivered', 'opened', 'clicked', 'bounced']}
          height={220}
          loading={statsLoading}
        />
      </div>

      {/* ── Recent messages ───────────────────────────────────────────────── */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700">Recent Messages</h3>
          <Link to="/messages"
                className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700">
            View all <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {msgsLoading ? (
          <div className="divide-y divide-gray-50">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="px-6 py-3 flex gap-4">
                <div className="h-4 flex-1 bg-gray-100 rounded animate-pulse" />
                <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
              </div>
            ))}
          </div>
        ) : msgsError ? (
          <div role="alert" className="px-6 py-8 text-center text-sm text-red-500">
            Failed to load messages.{' '}
            <button onClick={loadMessages} className="underline">Retry</button>
          </div>
        ) : !messages.length ? (
          <div className="px-6 py-14 text-center text-gray-400">
            <p className="text-3xl mb-2">📭</p>
            <p className="font-medium text-gray-600 mb-1">No messages yet</p>
            <p className="text-sm">
              Use the API to send your first email.{' '}
              <a href="/api/docs/" target="_blank" rel="noopener noreferrer"
                 className="text-indigo-600 hover:underline">
                API docs →
              </a>
            </p>
          </div>
        ) : (
          <table className="w-full text-sm" aria-label="Recent messages">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['To', 'Subject', 'Status', 'Sent at'].map(h => (
                  <th key={h}
                      className="px-5 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {messages.map(msg => {
                const badge = STATUS_BADGE[msg.status] ?? STATUS_BADGE.queued;
                return (
                  <tr key={msg.id}
                      className="hover:bg-gray-50 transition-colors cursor-pointer"
                      onClick={() => window.location.href = `/messages/${msg.id}`}
                      role="button"
                      tabIndex={0}
                      aria-label={`View message to ${msg.to_email}`}
                      onKeyDown={e => e.key === 'Enter' && (window.location.href = `/messages/${msg.id}`)}>
                    <td className="px-5 py-3 font-mono text-xs text-gray-600 max-w-[160px] truncate">
                      {/* Never render raw HTML — React escapes this */}
                      {msg.to_email}
                    </td>
                    <td className="px-5 py-3 text-gray-700 max-w-[220px] truncate">
                      {msg.subject || '(no subject)'}
                    </td>
                    <td className="px-5 py-3">
                      <span className={`badge ${badge.cls}`}>{badge.label}</span>
                    </td>
                    <td className="px-5 py-3 text-gray-400 text-xs whitespace-nowrap">
                      {safeDate(msg.queued_at)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

    </div>
  );
}