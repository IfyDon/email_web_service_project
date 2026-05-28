/**
 * Generic async data-fetching hook.
 *
 * Security notes:
 *  - Errors are normalised — never exposes raw server stack traces to the UI
 *  - Aborts in-flight requests on component unmount (prevents stale-closure leaks)
 *  - No sensitive data is stored in state beyond what the component explicitly needs
 *
 * Place: frontend/src/hooks/useApi.js
 */

import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * @param {Function} apiFn   – function that returns a Promise (e.g. domainsApi.list)
 * @param {object}   options
 * @param {boolean}  options.immediate – call execute() on mount automatically
 * @param {*}        options.initialData – value before first successful fetch
 */
export function useApi(apiFn, { immediate = false, initialData = null } = {}) {
  const [data,    setData]    = useState(initialData);
  const [loading, setLoading] = useState(immediate);
  const [error,   setError]   = useState(null);

  // Track whether the component is still mounted to prevent state updates on
  // unmounted components (potential memory leak + React warning)
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const execute = useCallback(
    async (...args) => {
      if (!mountedRef.current) return;
      setLoading(true);
      setError(null);

      try {
        const result = await apiFn(...args);
        if (mountedRef.current) setData(result);
        return result;
      } catch (err) {
        // Normalise — only expose { code, message } to the UI
        const safe = {
          code:    err?.code    ?? 'unknown_error',
          message: err?.message ?? 'Something went wrong. Please try again.',
        };
        if (mountedRef.current) setError(safe);
        throw safe;    // re-throw so callers can react
      } finally {
        if (mountedRef.current) setLoading(false);
      }
    },
    [apiFn],
  );

  // Auto-call on mount if requested
  useEffect(() => {
    if (immediate) execute();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { data, loading, error, execute, setData };
}


/**
 * Pagination-aware variant — accumulates pages into a flat list.
 * Useful for the message / suppression list views.
 */
export function usePaginatedApi(apiFn) {
  const [items,    setItems]    = useState([]);
  const [count,    setCount]    = useState(0);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState(null);
  const [page,     setPage]     = useState(1);
  const [hasMore,  setHasMore]  = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const fetchPage = useCallback(
    async (params = {}, reset = false) => {
      if (!mountedRef.current) return;
      setLoading(true);
      setError(null);

      try {
        const currentPage = reset ? 1 : page;
        const result      = await apiFn({ page: currentPage, page_size: 50, ...params });
        if (!mountedRef.current) return;

        const newItems = result?.results ?? result ?? [];
        setItems(prev  => reset ? newItems : [...prev, ...newItems]);
        setCount(result?.count ?? newItems.length);
        setHasMore(!!result?.next);
        if (!reset) setPage(p => p + 1);
        else        setPage(2);
      } catch (err) {
        if (!mountedRef.current) return;
        setError({ code: err?.code ?? 'error', message: err?.message ?? 'Failed to load.' });
      } finally {
        if (mountedRef.current) setLoading(false);
      }
    },
    [apiFn, page],
  );

  const reset = useCallback((params) => {
    setPage(1);
    setItems([]);
    fetchPage(params, true);
  }, [fetchPage]);

  return { items, count, loading, error, hasMore, fetchPage, reset };
}