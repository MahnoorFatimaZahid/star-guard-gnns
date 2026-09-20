'use client';

import { useCallback } from 'react';
import { api } from '../lib/api';
import { useApi, LoadingBlock, ErrorBlock } from '../lib/useApi';

export default function KpiRow() {
  const fetcher = useCallback(() => api.getStats(), []);
  const { data, loading, error } = useApi(fetcher);

  if (loading) return <LoadingBlock label="Loading KPIs…" />;
  if (error) return <ErrorBlock message={error} />;

  const kpis = data?.kpis || [];

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))',
        gap: 16,
        marginBottom: 16
      }}
    >
      {kpis.map((k) => (
        <div
          key={k.label}
          style={{
            background: k.bg,
            borderRadius: 22,
            padding: '22px 24px',
            display: 'flex',
            flexDirection: 'column',
            gap: 14
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <p style={{ fontSize: 14, fontWeight: 600, color: k.labelInk, margin: 0 }}>{k.label}</p>
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: k.labelInk,
                background: 'rgba(6,37,26,0.12)',
                borderRadius: 999,
                padding: '3px 9px'
              }}
            >
              {k.badge}
            </span>
          </div>

          <p
            style={{
              fontSize: 38,
              fontWeight: 800,
              color: k.ink,
              margin: 0,
              lineHeight: 1,
              letterSpacing: '-0.02em'
            }}
          >
            {k.value}
          </p>

          {k.path ? (
            <svg viewBox="0 0 200 40" style={{ width: '100%', height: 34 }} aria-hidden="true">
              <path d={k.path} fill="none" stroke={k.ink} strokeWidth="2.4" strokeLinecap="round" />
            </svg>
          ) : (
            <p style={{ fontSize: 13, fontWeight: 500, color: k.ink, margin: 0, opacity: 0.75 }}>
              {k.note}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
