'use client';

import { useCallback } from 'react';
import { api } from '../lib/api';
import { useApi, LoadingBlock, ErrorBlock } from '../lib/useApi';
import { chip } from './ui';

const AVATARS = [
  ['JD', '#F5C8D0', '#3D1620'],
  ['MK', '#C9D8F7', '#17244A'],
  ['RS', '#F8DCA8', '#42300C']
];

export default function Repos() {
  const fetcher = useCallback(() => api.getRepos({ limit: 30, sort: 'score' }), []);
  const { data, loading, error } = useApi(fetcher);

  if (loading) return <LoadingBlock label="Loading suspicious repos…" />;
  if (error) return <ErrorBlock message={error} />;

  const REPOS = data?.repos || [];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(360px,1fr))', gap: 16 }}>
      {REPOS.map((r) => (
        <div
          key={r.name}
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--line)',
            borderRadius: 24,
            padding: '24px 26px',
            minWidth: 0
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 14 }}>
            <div style={{ minWidth: 0 }}>
              <p
                className="mono"
                style={{
                  fontSize: 15,
                  color: 'var(--ink)',
                  margin: 0,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}
              >
                {r.name}
              </p>
              <p style={{ fontSize: 13, color: 'var(--ink-faint)', margin: '5px 0 0' }}>{r.meta}</p>
            </div>
            <div style={{ textAlign: 'right', flex: 'none' }}>
              <p style={{ fontSize: 24, fontWeight: 700, margin: 0, color: r.color }}>{r.score}</p>
              <p className="mono" style={{ fontSize: 11, color: 'var(--ink-dim)', margin: '2px 0 0' }}>
                RISK
              </p>
            </div>
          </div>

          <svg viewBox="0 0 320 110" style={{ width: '100%', height: 'auto', marginTop: 16 }}>
            <g stroke="#17181C" strokeWidth="1">
              <line x1="0" y1="95" x2="320" y2="95" />
              <line x1="0" y1="60" x2="320" y2="60" />
              <line x1="0" y1="25" x2="320" y2="25" />
            </g>
            <path d={r.path} fill="none" stroke={r.color} strokeWidth="3" strokeLinecap="round" />
            <text
              x="318"
              y="16"
              fontFamily="var(--font-mono), monospace"
              fontSize="11"
              fill="#7A8290"
              textAnchor="end"
            >
              {r.stars}
            </text>
          </svg>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 14 }}>
            {r.tags.map((t) => (
              <span key={t} style={chip}>{t}</span>
            ))}
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              marginTop: 16,
              paddingTop: 16,
              borderTop: '1px solid var(--line-soft)'
            }}
          >
            <div style={{ display: 'flex' }}>
              {AVATARS.map(([initials, bg, ink], i) => (
                <span
                  key={initials}
                  style={{
                    width: 26,
                    height: 26,
                    borderRadius: '50%',
                    background: bg,
                    border: '2px solid var(--surface)',
                    color: ink,
                    fontSize: 10,
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginLeft: i === 0 ? 0 : -8
                  }}
                >
                  {initials}
                </span>
              ))}
            </div>
            <p style={{ fontSize: 13, color: 'var(--ink-faint)', margin: 0 }}>{r.flagged}</p>
            <a href={r.url} target="_blank" rel="noreferrer" style={{ marginLeft: 'auto', fontSize: 13, fontWeight: 600 }}>
              Inspect
            </a>
          </div>
        </div>
      ))}
    </div>
  );
}
