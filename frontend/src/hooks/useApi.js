/*
 * Generic async data-fetching hook.
 * Wraps an API call with loading / error / data state.
 *
 * Usage:
 *   const { data, loading, error, execute } = useApi(domainsApi.list);
 *   useEffect(() => { execute(); }, []);
 *
 * Place: frontend/src/hooks/useApi.js
 */

/*
import { useState, useCallback } from 'react';

export function useApi(apiFn, { immediate = false } = {}) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error,   setError]   = useState(null);

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFn(...args);
      setData(result);
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFn]);

  return { data, loading, error, execute, setData };
}
*/