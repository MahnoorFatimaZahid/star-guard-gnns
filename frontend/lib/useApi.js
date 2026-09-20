'use client';
import { useEffect, useState, useCallback } from 'react';

// Small shared data-fetching hook so every component doesn't repeat the
// same loading/error boilerplate. `fetcher` should be a stable function
// (define it outside the component, or wrap with useCallback) that
// returns a promise from lib/api.js.
export function useApi(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadTick, setReloadTick] = useState(0);

  const reload = useCallback(() => setReloadTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetcher()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadTick]);

  return { data, loading, error, reload };
}

export function LoadingBlock({ label = 'Loading…' }) {
  return (
    <div
      style={{
        padding: '60px 20px',
        textAlign: 'center',
        color: 'var(--ink-faint)',
        fontSize: 14,
      }}
    >
      {label}
    </div>
  );
}

export function ErrorBlock({ message }) {
  return (
    <div
      style={{
        padding: '40px 20px',
        textAlign: 'center',
        color: '#F5C8D0',
        fontSize: 14,
        background: 'var(--surface)',
        border: '1px solid var(--line)',
        borderRadius: 16,
      }}
    >
      Couldn&apos;t reach the API — {message}
      <div style={{ marginTop: 8, fontSize: 12, color: 'var(--ink-faint)' }}>
        Is the backend running at{' '}
        {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}?
      </div>
    </div>
  );
}
