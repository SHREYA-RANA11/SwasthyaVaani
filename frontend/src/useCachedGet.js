import { useCallback, useEffect, useState } from 'react';
import API, { errorMessage } from './api';
import { useAuth } from './useAuth';

// GET that remembers its last good answer on the device. When the network is
// down it returns the saved copy, so patients can still read old prescriptions.
export function useCachedGet(url, { params, cacheKey } = {}) {
  const { user } = useAuth();
  const [version, setVersion] = useState(0);
  const [state, setState] = useState({});
  const paramsKey = JSON.stringify(params || {});
  const storageKey = `sv:${user.id}:${cacheKey || url}`;

  useEffect(() => {
    let alive = true;
    API.get(url, { params: JSON.parse(paramsKey) })
      .then((res) => {
        try {
          localStorage.setItem(storageKey, JSON.stringify({ data: res.data, savedAt: Date.now() }));
        } catch { /* storage full or blocked: ignore */ }
        if (alive) setState({ data: res.data, offline: false });
      })
      .catch((err) => {
        if (!alive) return;
        if (!err.response) {
          try {
            const saved = JSON.parse(localStorage.getItem(storageKey));
            if (saved) return setState({ data: saved.data, offline: true, savedAt: saved.savedAt });
          } catch { /* fall through */ }
        }
        setState({ error: errorMessage(err) });
      });
    return () => { alive = false; };
  }, [url, paramsKey, storageKey, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  const loading = state.data === undefined && !state.error;
  return { ...state, loading, reload };
}
