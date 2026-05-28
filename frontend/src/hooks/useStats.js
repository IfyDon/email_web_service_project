/**
 * Stats data-fetching hook.
 * Wraps the /api/v1/stats/ endpoint with caching, date-range validation,
 * and safe defaults so charts never render with undefined values.
 *
 * Place: frontend/src/hooks/useStats.js
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { subDays, format, isValid, parseISO } from 'date-fns';
import { statsApi } from '@/api/stats';

const FMT = 'yyyy-MM-dd';

/** Zero-filled summary object — safe default before data loads */
const EMPTY_SUMMARY = {
  sent: 0, delivered: 0, opened: 0, clicked: 0,
  bounced: 0, complained: 0, failed: 0, unsubscribed: 0,
  open_rate: 0, click_rate: 0, bounce_rate: 0, complaint_rate: 0,
};

/** Sanitise a single summary object from the API */
function sanitiseSummary(raw) {
  if (!raw || typeof raw !== 'object') return EMPTY_SUMMARY;
  const nums = {};
  for (const k of Object.keys(EMPTY_SUMMARY)) {
    const v = Number(raw[k]);
    nums[k] = Number.isFinite(v) && v >= 0 ? v : 0;
  }
  return nums;
}

/** Sanitise the timeline array */
function sanitiseTimeline(raw) {
  if (!Array.isArray(raw)) return [];
  return raw.map(row => ({
    date:       String(row?.date ?? ''),
    sent:       Math.max(0, Number(row?.sent)       || 0),
    delivered:  Math.max(0, Number(row?.delivered)  || 0),
    opened:     Math.max(0, Number(row?.opened)     || 0),
    clicked:    Math.max(0, Number(row?.clicked)    || 0),
    bounced:    Math.max(0, Number(row?.bounced)    || 0),
    complained: Math.max(0, Number(row?.complained) || 0),
    failed:     Math.max(0, Number(row?.failed)     || 0),
  }));
}

/**
 * @param {object} opts
 * @param {number}  opts.days         – default range in days (default: 30)
 * @param {string}  opts.granularity  – 'summary' | 'daily' (default: 'daily')
 * @param {string|null} opts.domain   – filter by sending domain
 */
export function useStats({
  days        = 30,
  granularity = 'daily',
  domain      = null,
} = {}) {
  const today     = new Date();
  const defaultFrom = format(subDays(today, days - 1), FMT);
  const defaultTo   = format(today, FMT);

  const [dateFrom,  setDateFrom]  = useState(defaultFrom);
  const [dateTo,    setDateTo]    = useState(defaultTo);
  const [summary,   setSummary]   = useState(EMPTY_SUMMARY);
  const [timeline,  setTimeline]  = useState([]);
  const [topDomains, setTopDomains] = useState([]);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const fetchStats = useCallback(async (from = dateFrom, to = dateTo) => {
    // Client-side date validation to prevent invalid API calls
    const parsedFrom = parseISO(from);
    const parsedTo   = parseISO(to);
    if (!isValid(parsedFrom) || !isValid(parsedTo) || parsedFrom > parsedTo) {
      setError({ code: 'invalid_date', message: 'Invalid date range.' });
      return;
    }

    if (!mountedRef.current) return;
    setLoading(true);
    setError(null);

    try {
      const params = { from, to, granularity };
      if (domain) params.domain = domain;

      const data = await statsApi.get(params);
      if (!mountedRef.current) return;

      setSummary(sanitiseSummary(data?.summary));
      setTimeline(sanitiseTimeline(data?.timeline));
      setTopDomains(Array.isArray(data?.top_domains) ? data.top_domains : []);
    } catch (err) {
      if (!mountedRef.current) return;
      setError({ code: err?.code ?? 'fetch_error', message: err?.message ?? 'Failed to load stats.' });
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [dateFrom, dateTo, granularity, domain]);

  // Auto-fetch on mount and when params change
  useEffect(() => { fetchStats(dateFrom, dateTo); }, [dateFrom, dateTo, domain]);

  const setRange = useCallback((from, to) => {
    setDateFrom(from);
    setDateTo(to);
  }, []);

  return {
    summary, timeline, topDomains,
    loading, error,
    dateFrom, dateTo, setRange,
    refetch: () => fetchStats(dateFrom, dateTo),
  };
}